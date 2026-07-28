import React, { createContext, useState, useContext, ReactNode } from 'react';
import api from '../lib/api';

interface Player {
  id: string;
  name: string;
  number: number;
  position: string;
  team: {
    id: string;
    name: string;
    short_name: string;
    shield_url: string;
  };
}

interface LineupState {
  [key: string]: Player;
}

interface FantasyContextType {
  lineup: LineupState;
  dtTeam: any;
  setPlayer: (position: string, player: Player) => void;
  removePlayer: (position: string) => void;
  setDTTeam: (team: any) => void;
  isLineupComplete: () => boolean;
  submitLineup: (jornadaId: string, token: string) => Promise<void>;
  clearLineup: () => void;
  hasPlayer: (playerId: string) => boolean;
}

const FantasyContext = createContext<FantasyContextType | undefined>(undefined);

export function FantasyProvider({ children }: { children: ReactNode }) {
  const [lineup, setLineup] = useState<LineupState>({});
  const [dtTeam, setDTTeamState] = useState<any>(null);

  const setPlayer = (position: string, player: Player) => {
    setLineup(prev => ({
      ...prev,
      [position]: player,
    }));
  };

  const removePlayer = (position: string) => {
    setLineup(prev => {
      const newLineup = { ...prev };
      delete newLineup[position];
      return newLineup;
    });
  };

  const setDTTeam = (team: any) => {
    setDTTeamState(team);
  };

  const isLineupComplete = () => {
    const requiredPositions = [
      'GK_1',
      'DF_1', 'DF_2', 'DF_3', 'DF_4',
      'MF_1', 'MF_2', 'MF_3', 'MF_4',
      'FW_1', 'FW_2',
    ];
    return requiredPositions.every(pos => lineup[pos]) && dtTeam !== null;
  };

  const hasPlayer = (playerId: string) => {
    return Object.values(lineup).some(player => player.id === playerId);
  };

  const submitLineup = async (jornadaId: string, _token: string) => {
    console.log('📤 [FantasyContext] submitLineup: Enviando alineación...');
    const playersArray = Object.entries(lineup).map(([slot, player]) => ({
      player_id: player.id,
      position_slot: slot,
    }));

    try {
      // Usa la instancia api centralizada - el interceptor agrega el token automáticamente
      await api.post('/api/fantasy/lineup', {
        jornada_id: jornadaId,
        players: playersArray,
        dt_team_id: dtTeam?.id,
      });
      console.log('✅ [FantasyContext] submitLineup: Alineación enviada');
    } catch (error) {
      console.error('❌ [FantasyContext] submitLineup error:', error);
      throw error;
    }
  };

  const clearLineup = () => {
    setLineup({});
    setDTTeamState(null);
  };

  return (
    <FantasyContext.Provider
      value={{
        lineup,
        dtTeam,
        setPlayer,
        removePlayer,
        setDTTeam,
        isLineupComplete,
        submitLineup,
        clearLineup,
        hasPlayer,
      }}
    >
      {children}
    </FantasyContext.Provider>
  );
}

export function useFantasy() {
  const context = useContext(FantasyContext);
  if (context === undefined) {
    throw new Error('useFantasy must be used within a FantasyProvider');
  }
  return context;
}