from aiogram.fsm.state import StatesGroup, State

class Reg(StatesGroup):
    name = State()
    phone = State()
    role = State()
    studio_name = State()
    description = State()
    contact_data = State()
    shoot_type = State()


class UploadContent(StatesGroup):
    waiting_for_file = State()
    waiting_for_description = State()

class Review(StatesGroup):
    waiting_for_studios = State()
    waiting_for_text = State()

class Complaint(StatesGroup):
    waiting_for_studio= State()
    waiting_for_text = State()

class EditStudio(StatesGroup):
    name = State()
    description = State()
    contact = State()
    shoot_type = State()

class EditPortfolio(StatesGroup):
    waiting_for_description = State()

class PortfolioPagination(StatesGroup):
    viewing = State()

class StudioReviews(StatesGroup):
    viewing_reviews = State()

class ReviewPage(StatesGroup):
    show_review_page = State()

class AdminStates(StatesGroup):
    managing_studios = State()
    managing_clients = State()
    searching_studio = State()
    searching_client = State()


class PortfolioPaginationClient(StatesGroup):
    viewing = State()