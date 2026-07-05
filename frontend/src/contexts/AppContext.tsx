import React, { createContext, useContext, useState, useEffect } from 'react';
import { listOrganizations, listTeams } from '../api/lookups';
import { OrganizationLookup, TeamLookup } from '../types/lookup';

interface AppContextProps {
  selectedOrgId: string;
  setSelectedOrgId: (id: string) => void;
  selectedTeamId: string;
  setSelectedTeamId: (id: string) => void;
  organizations: OrganizationLookup[];
  teams: TeamLookup[];
  isLoadingContext: boolean;
  refreshContext: () => Promise<void>;
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

const AppContext = createContext<AppContextProps | undefined>(undefined);

export function AppContextProvider({ children }: { children: React.ReactNode }) {
  const [selectedOrgId, setSelectedOrgId] = useState<string>(() => {
    return localStorage.getItem('fitnova_org_id') || '';
  });
  const [selectedTeamId, setSelectedTeamId] = useState<string>(() => {
    return localStorage.getItem('fitnova_team_id') || '';
  });
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    const val = localStorage.getItem('fitnova_sidebar_open');
    return val === null ? true : val === 'true';
  });

  const [organizations, setOrganizations] = useState<OrganizationLookup[]>([]);
  const [teams, setTeams] = useState<TeamLookup[]>([]);
  const [isLoadingContext, setIsLoadingContext] = useState(true);

  async function loadMetadata() {
    try {
      setIsLoadingContext(true);
      const orgs = await listOrganizations();
      setOrganizations(orgs);
      
      // Auto-select first org if none selected or if selected is not valid
      let activeOrgId = selectedOrgId;
      if (orgs.length > 0) {
        const found = orgs.find(o => o.id === selectedOrgId);
        if (!found) {
          activeOrgId = orgs[0].id;
          setSelectedOrgId(activeOrgId);
        }
      }

      if (activeOrgId) {
        const t = await listTeams(activeOrgId);
        setTeams(t);
        // Clear team selection if not valid for the new org
        if (selectedTeamId) {
          const foundTeam = t.find(team => team.id === selectedTeamId);
          if (!foundTeam) {
            setSelectedTeamId('');
          }
        }
      } else {
        setTeams([]);
      }
    } catch (err) {
      console.error('Failed to load context lookups:', err);
    } finally {
      setIsLoadingContext(false);
    }
  }

  useEffect(() => {
    loadMetadata();
  }, []);

  // Update teams list when org changes
  useEffect(() => {
    if (selectedOrgId) {
      localStorage.setItem('fitnova_org_id', selectedOrgId);
      listTeams(selectedOrgId)
        .then((t) => {
          setTeams(t);
          // If the selected team is not in the new teams list, clear it
          if (selectedTeamId && !t.some(team => team.id === selectedTeamId)) {
            setSelectedTeamId('');
            localStorage.removeItem('fitnova_team_id');
          }
        })
        .catch(err => console.error('Failed to update teams:', err));
    } else {
      localStorage.removeItem('fitnova_org_id');
      setTeams([]);
      setSelectedTeamId('');
      localStorage.removeItem('fitnova_team_id');
    }
  }, [selectedOrgId]);

  useEffect(() => {
    if (selectedTeamId) {
      localStorage.setItem('fitnova_team_id', selectedTeamId);
    } else {
      localStorage.removeItem('fitnova_team_id');
    }
  }, [selectedTeamId]);

  useEffect(() => {
    localStorage.setItem('fitnova_sidebar_open', String(sidebarOpen));
  }, [sidebarOpen]);

  return (
    <AppContext.Provider
      value={{
        selectedOrgId,
        setSelectedOrgId,
        selectedTeamId,
        setSelectedTeamId,
        organizations,
        teams,
        isLoadingContext,
        refreshContext: loadMetadata,
        sidebarOpen,
        setSidebarOpen,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppGlobalContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppGlobalContext must be used within an AppContextProvider');
  }
  return context;
}
