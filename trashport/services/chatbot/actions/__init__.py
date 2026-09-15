from .base import BaseChatAction
from .schedule_pickup import SchedulePickupAction
from .change_schedule import ChangeScheduleAction
from .cancel_pickup import CancelPickupAction
from .navigate import NavigateAction
from .track_collector import TrackCollectorAction
from .file_complaint import FileComplaintAction
from .check_payment import CheckPaymentAction
from .general_answer import GeneralAnswerAction
from ..intent.intents import IntentType

ACTION_ROUTER = {
    IntentType.SCHEDULE_PICKUP: SchedulePickupAction(),
    IntentType.CHANGE_SCHEDULE: ChangeScheduleAction(),
    IntentType.CANCEL_PICKUP: CancelPickupAction(),
    IntentType.TRACK_COLLECTOR: TrackCollectorAction(),
    IntentType.FILE_COMPLAINT: FileComplaintAction(),
    IntentType.CHECK_PAYMENT: CheckPaymentAction(),
    IntentType.NAVIGATE: NavigateAction(),
    IntentType.GENERAL_ANSWER: GeneralAnswerAction(),
}

__all__ = [
    "BaseChatAction",
    "SchedulePickupAction",
    "ChangeScheduleAction",
    "CancelPickupAction",
    "NavigateAction",
    "TrackCollectorAction",
    "FileComplaintAction",
    "CheckPaymentAction",
    "GeneralAnswerAction",
    "ACTION_ROUTER",
]
