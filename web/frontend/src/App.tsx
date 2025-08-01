import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Box, Container } from '@mui/material'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Tasks from './pages/Tasks'
import ClaudeEditor from './pages/ClaudeEditor'
import Settings from './pages/Settings'

function App() {
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
          </Routes>
        </Box>
      </Container>
    </Layout>
  )
}

export default App