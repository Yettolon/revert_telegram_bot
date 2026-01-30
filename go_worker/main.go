package main

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"time"

	_ "github.com/lib/pq"
)

func main() {
	// Настраиваем логирование
	setupLogger()

	if len(os.Args) < 2 {
		log.Fatal("Usage: go_worker <command>")
	}

	command := os.Args[1]

	switch command {
	case "daemon":
		runDaemon()
	case "check-positions":
		checkPositions()
	case "echo":
		if len(os.Args) < 4 {
			log.Fatal("Usage: go_worker echo <chat_id> <message>")
		}
		chatID, _ := strconv.ParseInt(os.Args[2], 10, 64)
		message := os.Args[3]
		sendEcho(chatID, message)
	case "test-db":
		testDB()
	default:
		log.Fatalf("Unknown command: %s", command)
	}
}

func setupLogger() {
	// Создаем директорию logs если не существует
	logsDir := getEnv("LOGS_DIR", "logs")
	if err := os.MkdirAll(logsDir, 0755); err != nil {
		log.Printf("⚠️  Failed to create logs directory: %v", err)
		return
	}

	// Открываем файл для логов
	logFile := filepath.Join(logsDir, "go_worker.log")
	file, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		log.Printf("⚠️  Failed to open log file: %v", err)
		return
	}

	// Пишем и в stdout и в файл
	multiWriter := io.MultiWriter(os.Stdout, file)
	log.SetOutput(multiWriter)
	log.SetFlags(log.Ldate | log.Ltime | log.Lshortfile)

	log.Println("📝 Logger initialized, writing to:", logFile)
}

func runDaemon() {
	intervalStr := getEnv("UPDATE_INTERVAL", "300")
	interval, err := strconv.Atoi(intervalStr)
	if err != nil {
		log.Fatalf("Invalid UPDATE_INTERVAL: %v", err)
	}

	log.Printf("🚀 Go worker daemon started (interval: %d seconds)", interval)

	checkPositions()

	ticker := time.NewTicker(time.Duration(interval) * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		checkPositions()
	}
}

// ============================================================================
// DATABASE
// ============================================================================

func connectDB() *sql.DB {
	dsn := fmt.Sprintf(
		"postgres://%s:%s@%s:%s/%s?sslmode=disable",
		getEnv("DB_USER", "bot_user"),
		getEnv("DB_PASSWORD", ""),
		getEnv("DB_HOST", "localhost"),
		getEnv("DB_PORT", "5432"),
		getEnv("DB_NAME", "revert_bot"),
	)

	db, err := sql.Open("postgres", dsn)
	if err != nil {
		log.Fatalf("Failed to connect to DB: %v", err)
	}

	db.SetMaxOpenConns(5)
	db.SetMaxIdleConns(2)
	db.SetConnMaxLifetime(time.Hour)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := db.PingContext(ctx); err != nil {
		log.Fatalf("Failed to ping DB: %v", err)
	}

	return db
}

func testDB() {
	log.Println("🔌 Testing database connection...")
	db := connectDB()
	defer db.Close()

	var count int
	err := db.QueryRow("SELECT COUNT(*) FROM positions").Scan(&count)
	if err != nil {
		log.Fatalf("Query failed: %v", err)
	}

	log.Printf("✅ Database OK! Found %d positions", count)
}

// ============================================================================
// TELEGRAM
// ============================================================================

func sendEcho(chatID int64, message string) {
	botToken := os.Getenv("BOT_TOKEN")
	if botToken == "" {
		log.Fatal("BOT_TOKEN not set")
	}

	url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", botToken)

	payload := map[string]interface{}{
		"chat_id": chatID,
		"text":    fmt.Sprintf("🤖 Echo from Go:\n\n%s", message),
	}

	jsonData, _ := json.Marshal(payload)

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		log.Fatalf("Failed to send message: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		log.Fatalf("Telegram API error: %s", body)
	}

	log.Printf("✅ Echo sent to chat %d", chatID)
}

func sendTelegramMessage(chatID int64, text string, keyboard interface{}) error {
	botToken := os.Getenv("BOT_TOKEN")
	url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", botToken)

	payload := map[string]interface{}{
		"chat_id":    chatID,
		"text":       text,
		"parse_mode": "HTML",
	}

	if keyboard != nil {
		payload["reply_markup"] = keyboard
	}

	jsonData, _ := json.Marshal(payload)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	req, _ := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("telegram API error: %s", body)
	}

	return nil
}

// ============================================================================
// REVERT API
// ============================================================================

type RevertResponse struct {
	Success bool `json:"success"`
	Data    struct {
		Exited     bool    `json:"exited"`
		InRange    bool    `json:"in_range"`
		PoolPrice  *string `json:"pool_price"`
		PriceLower *string `json:"price_lower"`
		PriceUpper *string `json:"price_upper"`
		FeesValue  *string `json:"fees_value"`
	} `json:"data"`
}

func parseFloat(s *string) *float64 {
	if s == nil {
		return nil
	}
	f, err := strconv.ParseFloat(*s, 64)
	if err != nil {
		return nil
	}
	return &f
}

func fetchRevertData(url string) (*RevertResponse, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	var data RevertResponse
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}

	if !data.Success {
		return nil, fmt.Errorf("API returned success=false")
	}

	return &data, nil
}

// ============================================================================
// POSITION CHECKER
// ============================================================================
func checkPositions() {
	log.Println("🔍 Starting position check...")

	db := connectDB()
	defer db.Close()

	rows, err := db.Query(`
		SELECT DISTINCT 
			p.id, p.original_url, p.exchange, p.network, p.nft_id,
			p.token_1_symbol, p.token_2_symbol, p.is_in_range
		FROM positions p
		INNER JOIN user_positions up ON p.id = up.position_id
		WHERE up.is_active = true
	`)
	if err != nil {
		log.Fatalf("Query failed: %v", err)
	}
	defer rows.Close()

	count := 0
	for rows.Next() {
		var (
			id         int
			url        string
			exchange   string
			network    string
			nftID      string
			token1     sql.NullString
			token2     sql.NullString
			oldInRange bool
		)

		err := rows.Scan(&id, &url, &exchange, &network, &nftID, &token1, &token2, &oldInRange)
		if err != nil {
			log.Printf("❌ Scan error: %v", err)
			continue
		}

		count++
		log.Printf("📊 [%d] Checking position %d (NFT: %s)", count, id, nftID)

		data, err := fetchRevertData(url)
		if err != nil {
			log.Printf("❌ API error for position %d: %v", id, err)
			continue
		}

		poolPrice := parseFloat(data.Data.PoolPrice)
		priceLower := parseFloat(data.Data.PriceLower)
		priceUpper := parseFloat(data.Data.PriceUpper)
		feesValue := parseFloat(data.Data.FeesValue)

		if data.Data.Exited {
			log.Printf("🔒 Position %d is closed (exited=true)", id)
			handleClosedPosition(db, id, exchange, network, nftID, token1, token2)
			continue
		}

		_, err = db.Exec(`
			UPDATE positions 
			SET is_in_range = $1, current_price = $2, min_price = $3, 
			    max_price = $4, total_fees_usd = $5
			WHERE id = $6
		`, data.Data.InRange, poolPrice, priceLower, priceUpper, feesValue, id)

		if err != nil {
			log.Printf("❌ Update error for position %d: %v", id, err)
			continue
		}

		if oldInRange != data.Data.InRange {
			log.Printf("🔔 Status changed: %v → %v", oldInRange, data.Data.InRange)
			notifyStatusChange(db, id, exchange, network, nftID, token1, token2,
				oldInRange, data.Data.InRange, poolPrice, priceLower, priceUpper)
		}

		time.Sleep(100 * time.Millisecond)
	}

	log.Printf("✅ Checked %d positions", count)
}

func handleClosedPosition(db *sql.DB, posID int, exchange, network, nftID string,
	token1, token2 sql.NullString) {

	rows, err := db.Query(`
		SELECT u.telegram_id
		FROM users u
		INNER JOIN user_positions up ON u.id = up.user_id
		WHERE up.position_id = $1 AND up.is_active = true
	`, posID)
	if err != nil {
		log.Printf("❌ Failed to get users: %v", err)
		return
	}
	defer rows.Close()

	var userIDs []int64
	for rows.Next() {
		var id int64
		rows.Scan(&id)
		userIDs = append(userIDs, id)
	}

	log.Printf("📤 Sending closed notifications to %d users", len(userIDs))

	t1 := "?"
	if token1.Valid {
		t1 = token1.String
	}
	t2 := "?"
	if token2.Valid {
		t2 = token2.String
	}

	message := fmt.Sprintf(
		"🔒 <b>Position closed!</b>\n\n"+
			"<b>%s/%s</b>\n"+
			"Exchange: %s\n"+
			"Network: %s\n"+
			"NFT ID: <code>%s</code>\n\n"+
			"This position has been closed and removed from tracking.",
		t1, t2, exchange, network, nftID,
	)

	revertURL := fmt.Sprintf("https://revert.finance/#/%s-position/%s/%s",
		exchange, network, nftID)

	keyboard := map[string]interface{}{
		"inline_keyboard": [][]map[string]string{
			{
				{"text": "🔗 View on Revert Finance", "url": revertURL},
			},
		},
	}

	for _, chatID := range userIDs {
		if err := sendTelegramMessage(chatID, message, keyboard); err != nil {
			log.Printf("❌ Failed to send to %d: %v", chatID, err)
		} else {
			log.Printf("✅ Closed notification sent to %d", chatID)
		}
	}

	_, err = db.Exec("DELETE FROM positions WHERE id = $1", posID)
	if err != nil {
		log.Printf("❌ Failed to delete position: %v", err)
	} else {
		log.Printf("🗑️ Position %d deleted", posID)
	}
}

func notifyStatusChange(db *sql.DB, posID int, exchange, network, nftID string,
	token1, token2 sql.NullString, oldStatus, newStatus bool,
	currentPrice, minPrice, maxPrice *float64) {

	rows, err := db.Query(`
		SELECT u.telegram_id
		FROM users u
		INNER JOIN user_positions up ON u.id = up.user_id
		WHERE up.position_id = $1 AND up.is_active = true
	`, posID)
	if err != nil {
		log.Printf("❌ Failed to get users: %v", err)
		return
	}
	defer rows.Close()

	var userIDs []int64
	for rows.Next() {
		var id int64
		rows.Scan(&id)
		userIDs = append(userIDs, id)
	}

	log.Printf("📤 Sending status change to %d users", len(userIDs))

	statusEmoji := "🔴"
	statusText := "Out of range"
	if newStatus {
		statusEmoji = "🟢"
		statusText = "In range"
	}

	t1 := "?"
	if token1.Valid {
		t1 = token1.String
	}
	t2 := "?"
	if token2.Valid {
		t2 = token2.String
	}

	boundaryInfo := ""
	if !newStatus && oldStatus && currentPrice != nil && minPrice != nil && maxPrice != nil {
		if *currentPrice < *minPrice {
			boundaryInfo = fmt.Sprintf("\n\n⬇️ Price dropped below minimum\nMin price: <code>%.6f</code>", *minPrice)
		} else if *currentPrice > *maxPrice {
			boundaryInfo = fmt.Sprintf("\n\n⬆️ Price rose above maximum\nMax price: <code>%.6f</code>", *maxPrice)
		}
	} else if newStatus && !oldStatus {
		boundaryInfo = "\n\n✅ Price returned to range"
	}

	priceInfo := ""
	if currentPrice != nil {
		priceInfo += fmt.Sprintf("\n\n💰 Current price: <code>%.6f</code>", *currentPrice)
	}
	if minPrice != nil && maxPrice != nil {
		priceInfo += fmt.Sprintf(
			"\n\n📊 Price range:\nMin: <code>%.6f</code>\nMax: <code>%.6f</code>",
			*minPrice, *maxPrice,
		)
	}

	message := fmt.Sprintf(
		"%s <b>Position status update!</b>\n\n"+
			"<b>%s/%s</b>\n"+
			"Exchange: %s\n"+
			"Network: %s\n"+
			"NFT ID: <code>%s</code>\n\n"+
			"Status: <b>%s</b>%s%s",
		statusEmoji, t1, t2, exchange, network, nftID, statusText, boundaryInfo, priceInfo,
	)

	revertURL := fmt.Sprintf("https://revert.finance/#/%s-position/%s/%s",
		exchange, network, nftID)

	keyboard := map[string]interface{}{
		"inline_keyboard": [][]map[string]string{
			{
				{"text": "🔗 View on Revert Finance", "url": revertURL},
			},
		},
	}

	successCount := 0
	for _, chatID := range userIDs {
		if err := sendTelegramMessage(chatID, message, keyboard); err != nil {
			log.Printf("❌ Failed to send to %d: %v", chatID, err)
		} else {
			successCount++
		}
	}

	log.Printf("✅ Status change notifications sent: %d/%d", successCount, len(userIDs))
}

// ============================================================================
// UTILS
// ============================================================================

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}