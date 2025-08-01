import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Button,
  Typography,
  Paper,
  CircularProgress,
  Alert,
} from '@mui/material'
import { Save as SaveIcon, ArrowBack as ArrowBackIcon } from '@mui/icons-material'
import Editor from '@monaco-editor/react'
import { useQuery, useMutation } from 'react-query'
import { claudeService } from '../services/api'

export default function ClaudeEditor() {
  const { role } = useParams<{ role: string }>()
  const navigate = useNavigate()
  const [content, setContent] = useState('')

  const { data, isLoading, error } = useQuery(
    ['claude', role],
    () => claudeService.getPrompt(role!).then((res) => res.data),
    {
      enabled: !!role,
      onSuccess: (data) => {
        setContent(data.content || '')
      },
    }
  )

  const saveMutation = useMutation(
    () => claudeService.updatePrompt(role!, content),
    {
      onSuccess: () => {
        // Show success notification
      },
    }
  )

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="60vh">
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return <Alert severity="error">Failed to load CLAUDE.md file</Alert>
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center">
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/agents')}
            sx={{ mr: 2 }}
          >
            Back
          </Button>
          <Typography variant="h4">
            Edit CLAUDE.md - {role?.toUpperCase()}
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isLoading}
        >
          Save
        </Button>
      </Box>

      <Paper sx={{ height: '70vh' }}>
        <Editor
          height="100%"
          defaultLanguage="markdown"
          value={content}
          onChange={(value) => setContent(value || '')}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: 'on',
          }}
        />
      </Paper>
    </Box>
  )
}