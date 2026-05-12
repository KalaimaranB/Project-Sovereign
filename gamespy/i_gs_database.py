from abc import ABC, abstractmethod

class IGamespyDatabase(ABC):
    """
    Abstract Contract following SOLID Dependency Inversion principle.
    Defines the complete domain logic surface for the database engine.
    Every method utilizes 'async def' to allow event-loop native drivers.
    """

    @abstractmethod
    async def initialize_database(self):
        """Setup initial schema structure."""
        pass

    @abstractmethod
    async def close(self):
        """Cleanly release connections."""
        pass

    # --- Profile & User Queries ---
    @abstractmethod
    async def check_user_exists(self, userid, gsbrcd):
        pass

    @abstractmethod
    async def check_user_enabled(self, userid, gsbrcd):
        pass

    @abstractmethod
    async def check_profile_exists(self, profileid):
        pass

    @abstractmethod
    async def get_profile_from_profileid(self, profileid):
        """Retrieves profile dictionary representation directly from atomic registry."""
        pass

    @abstractmethod
    async def get_nas_login_from_userid(self, userid):
        """Retrieves dynamic login session structure anchored by external system tokenizers."""
        pass

    @abstractmethod
    async def perform_login(self, userid, password, gsbrcd):
        pass

    @abstractmethod
    async def create_user(self, userid, password, email, uniquenick, gsbrcd,
                           console, csnum, cfc, bssid, devname, birth, gameid, macadr):
        pass

    @abstractmethod
    async def update_profile(self, profileid, field_dict):
        pass

    @abstractmethod
    async def get_next_free_profileid(self):
        pass

    # --- Session Management ---
    @abstractmethod
    async def create_session(self, profileid, loginticket):
        pass

    @abstractmethod
    async def get_profileid_from_session_key(self, session_key):
        pass

    @abstractmethod
    async def get_profile_from_session_key(self, session_key):
        pass

    @abstractmethod
    async def delete_session(self, profileid):
        pass

    # --- Buddy/Friends Network ---
    @abstractmethod
    async def add_buddy(self, userProfileId, buddyProfileId):
        pass

    @abstractmethod
    async def delete_buddy(self, userProfileId, buddyProfileId):
        pass

    @abstractmethod
    async def block_buddy(self, userProfileId, buddyProfileId):
        pass

    @abstractmethod
    async def get_buddy_list(self, userProfileId):
        pass

    @abstractmethod
    async def get_blocked_list(self, userProfileId):
        pass
        
    @abstractmethod
    async def get_pending_messages(self, profileid):
        pass
        
    @abstractmethod
    async def save_pending_message(self, sourceid, targetid, msg):
        pass
        
    @abstractmethod
    async def pd_insert(self, profileid, dindex, ptype, data):
        pass
        
    @abstractmethod
    async def pd_get(self, profileid, dindex, ptype):
        pass
        
    @abstractmethod
    async def get_nas_login(self, authtoken):
        pass

    @abstractmethod
    async def is_banned(self, postdata):
        pass

    @abstractmethod
    async def get_next_available_userid(self):
        pass

    @abstractmethod
    async def generate_authtoken(self, userid, data):
        pass
