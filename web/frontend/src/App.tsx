import React, { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Box, Container } from '@mui/material'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Tasks from './pages/Tasks'
import ClaudeEditor from './pages/ClaudeEditor'
import Settings from './pages/Settings'
import { WorkspaceSetup } from './components/WorkspaceSetup'
import { api } from './services/api'

function App() {
  const [workspaceInitialized, setWorkspaceInitialized] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkWorkspaceStatus();
  }, []);

  const checkWorkspaceStatus = async () => {
    try {
      const response = await api.get('/workspace/status');
      setWorkspaceInitialized(response.data.initialized);
    } catch (error: any) {
      console.error('Failed to check workspace status:', error);
      // If it's a 404, assume workspace is not initialized
      setWorkspaceInitialized(false);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">Loading...</Box>;
  }

  // If workspace not initialized, show setup
  if (!workspaceInitialized) {
    return (
      <Container maxWidth="xl">
        <Box sx={{ mt: 4 }}>
          <WorkspaceSetup />
        </Box>
      </Container>
    );
  }

  return (
    <Layout>
      <Container maxWidth="xl">
        <Box sx={{ mt: 4 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/claude/:role" element={<ClaudeEditor />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/workspace" element={<WorkspaceSetup />} />
          </Routes>
        </Box>
      </Container>
    </Layout>
  )
}

export default App