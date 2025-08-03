import React, { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Box, Container, CircularProgress } from '@mui/material'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Tasks from './pages/Tasks'
import ClaudeEditor from './pages/ClaudeEditor'
import { AppSettings } from './components/AppSettings'
import { WorkspaceSetup } from './components/WorkspaceSetup'
import { HomeSetup } from './components/HomeSetup'
import { ProjectList } from './components/ProjectList'
import { ProjectDetail } from './components/ProjectDetail'
import { AgentDetail } from './components/AgentDetail'
import api from './services/api'

function App() {
  const [appInitialized, setAppInitialized] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAppStatus();
  }, []);

  const checkAppStatus = async () => {
    try {
      const response = await api.get('/app/status');
      setAppInitialized(response.data.initialized);
    } catch (error: any) {
      console.error('Failed to check app status:', error);
      setAppInitialized(false);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  // If app not initialized, show home setup
  if (!appInitialized) {
    return <HomeSetup onInitialized={() => checkAppStatus()} />;
  }

  return (
    <Layout>
      <Container maxWidth="xl">
        <Box sx={{ mt: 4 }}>
          <Routes>
            <Route path="/" element={<ProjectList />} />
            <Route path="/projects" element={<ProjectList />} />
            <Route path="/projects/:projectId" element={<ProjectDetail />} />
            <Route path="/projects/:projectId/agents/:agentId" element={<AgentDetail />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/claude/:role" element={<ClaudeEditor />} />
            <Route path="/settings" element={<AppSettings />} />
            <Route path="/workspace" element={<WorkspaceSetup />} />
          </Routes>
        </Box>
      </Container>
    </Layout>
  )
}

export default App