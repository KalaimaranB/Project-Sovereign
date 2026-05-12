try:
    from gamespy.i_gs_cache import IGamespyCache
    print("ROOT IMPORT WORKED")
except ImportError:
    from i_gs_cache import IGamespyCache
    print("LOCAL IMPORT WORKED")
