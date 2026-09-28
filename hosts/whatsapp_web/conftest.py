import importlib.util

collect_ignore_glob = [] if importlib.util.find_spec("whatsapp_web") else ["*"]
