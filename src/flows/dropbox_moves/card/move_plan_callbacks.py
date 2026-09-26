from src.flows.dropbox_moves.card.move_plan_callback import MovePlanCallback

EXECUTE_CALLBACK = MovePlanCallback("dbx_moves_exec:")
CANCEL_CALLBACK = MovePlanCallback("dbx_moves_cancel:")
ROLLBACK_CALLBACK = MovePlanCallback("dbx_moves_undo:")
