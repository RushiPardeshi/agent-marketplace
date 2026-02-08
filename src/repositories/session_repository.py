"""
Repository abstraction for multi-agent session storage.
Provides an interface for state management with in-memory implementation.
Easy to swap for Postgres/Supabase later.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from src.models.schemas import MultiAgentSession, NegotiationState


class SessionRepository(ABC):
    """Abstract interface for session storage"""
    
    @abstractmethod
    def create_session(self, session: MultiAgentSession) -> str:
        """Create a new session and return its ID"""
        pass
    
    @abstractmethod
    def get_session(self, session_id: str) -> Optional[MultiAgentSession]:
        """Retrieve a session by ID"""
        pass
    
    @abstractmethod
    def update_session(self, session: MultiAgentSession) -> None:
        """Update an existing session"""
        pass
    
    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Delete a session, return True if successful"""
        pass
    
    @abstractmethod
    def list_sessions(self) -> List[str]:
        """List all session IDs"""
        pass
    
    @abstractmethod
    def add_negotiation(self, session_id: str, negotiation: NegotiationState) -> None:
        """Add a negotiation to a session"""
        pass
    
    @abstractmethod
    def update_negotiation(self, session_id: str, negotiation: NegotiationState) -> None:
        """Update a negotiation within a session"""
        pass
    
    @abstractmethod
    def get_negotiation(self, session_id: str, negotiation_id: str) -> Optional[NegotiationState]:
        """Get a specific negotiation from a session"""
        pass


class InMemorySessionRepository(SessionRepository):
    """In-memory implementation of SessionRepository"""
    
    def __init__(self):
        self._sessions: Dict[str, MultiAgentSession] = {}
    
    def create_session(self, session: MultiAgentSession) -> str:
        self._sessions[session.session_id] = session
        return session.session_id
    
    def get_session(self, session_id: str) -> Optional[MultiAgentSession]:
        return self._sessions.get(session_id)
    
    def update_session(self, session: MultiAgentSession) -> None:
        if session.session_id not in self._sessions:
            raise ValueError(f"Session {session.session_id} not found")
        self._sessions[session.session_id] = session
    
    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        return list(self._sessions.keys())
    
    def add_negotiation(self, session_id: str, negotiation: NegotiationState) -> None:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        session.active_negotiations[negotiation.negotiation_id] = negotiation
        self.update_session(session)
    
    def update_negotiation(self, session_id: str, negotiation: NegotiationState) -> None:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Update in active negotiations or move to completed
        if negotiation.status in ["agreed", "deadlocked"]:
            # Remove from active
            if negotiation.negotiation_id in session.active_negotiations:
                del session.active_negotiations[negotiation.negotiation_id]
            # Add to completed if not already there
            if negotiation not in session.completed_negotiations:
                session.completed_negotiations.append(negotiation)
        else:
            session.active_negotiations[negotiation.negotiation_id] = negotiation
        
        self.update_session(session)
    
    def get_negotiation(self, session_id: str, negotiation_id: str) -> Optional[NegotiationState]:
        session = self.get_session(session_id)
        if not session:
            return None
        return session.active_negotiations.get(negotiation_id)
