from aiogram.fsm.state import State, StatesGroup


class AddPositionStates(StatesGroup):
    choosing_exchange = State()
    choosing_network = State()
    entering_position_id = State()

    entering_url = State()
