import React, { useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  TextField,
  Typography,
  Alert,
  Divider,
} from '@mui/material'
import { Save as SaveIcon } from '@mui/icons-material'
import { useMutation } from 'react-query'
import { systemService, SystemConfig } from '../services/api'

export default function Settings() {
  const [config, setConfig] = useState<SystemConfig>({
    anthropic_api_key: '',
    telegram_bot_token: '',
    telegram_channel_id: '',
    github_token: '',
    github_repo: '',
  })

  const [success, setSuccess] = useState(false)

  const initializeMutation = useMutation(
    (data: SystemConfig) => systemService.initialize(data),
    {
      onSuccess: () => {
        setSuccess(true)
        setTimeout(() => setSuccess(false), 5000)
      },
    }
  )

  const handleSave = () => {
    initializeMutation.mutate(config)
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>

      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          System configuration updated successfully!
        </Alert>
      )}

      {initializeMutation.isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to update configuration. Please check your settings.
        </Alert>
      )}

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Claude API Configuration
          </Typography>
          <TextField
            fullWidth
            label="Anthropic API Key"
            type="password"
            value={config.anthropic_api_key}
            onChange={(e) =>
              setConfig({ ...config, anthropic_api_key: e.target.value })
            }
            helperText="Required for Claude API access"
            sx={{ mb: 3 }}
          />

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Telegram Integration (Optional)
          </Typography>
          <TextField
            fullWidth
            label="Telegram Bot Token"
            value={config.telegram_bot_token || ''}
            onChange={(e) =>
              setConfig({ ...config, telegram_bot_token: e.target.value })
            }
            helperText="Create a bot via @BotFather on Telegram"
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Telegram Channel ID"
            value={config.telegram_channel_id || ''}
            onChange={(e) =>
              setConfig({ ...config, telegram_channel_id: e.target.value })
            }
            helperText="Channel or group ID for notifications"
            sx={{ mb: 3 }}
          />

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            GitHub Integration (Optional)
          </Typography>
          <TextField
            fullWidth
            label="GitHub Personal Access Token"
            type="password"
            value={config.github_token || ''}
            onChange={(e) => setConfig({ ...config, github_token: e.target.value })}
            helperText="Token with repo access for issues and PRs"
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="GitHub Repository"
            value={config.github_repo || ''}
            onChange={(e) => setConfig({ ...config, github_repo: e.target.value })}
            placeholder="owner/repository"
            helperText="Format: owner/repository (e.g., username/project)"
            sx={{ mb: 3 }}
          />

          <Box display="flex" justifyContent="flex-end">
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
              disabled={!config.anthropic_api_key || initializeMutation.isLoading}
            >
              Save Configuration
            </Button>
          </Box>
        </CardContent>
      </Card>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Quick Start Guide
          </Typography>
          <Typography variant="body2" paragraph>
            1. <strong>Anthropic API Key:</strong> Get your API key from{' '}
            <a
              href="https://console.anthropic.com/"
              target="_blank"
              rel="noopener noreferrer"
            >
              console.anthropic.com
            </a>
          </Typography>
          <Typography variant="body2" paragraph>
            2. <strong>Telegram Bot (Optional):</strong> Create a bot using @BotFather
            on Telegram and get the bot token
          </Typography>
          <Typography variant="body2" paragraph>
            3. <strong>GitHub Token (Optional):</strong> Create a personal access token
            with repo permissions at{' '}
            <a
              href="https://github.com/settings/tokens"
              target="_blank"
              rel="noopener noreferrer"
            >
              github.com/settings/tokens
            </a>
          </Typography>
        </CardContent>
      </Card>
    </Box>
  )
}