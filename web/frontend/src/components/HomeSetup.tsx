import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  InputAdornment,
  Stack
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import FolderIcon from '@mui/icons-material/Folder';
import api from '../services/api';

interface HomeSetupProps {
  onInitialized: () => void;
}

interface SetupFormData {
  home_directory: string;
  primary_folder?: string;
  anthropic_api_key: string;
  github_token: string;
  telegram_bot_token: string;
  telegram_channel_id: string;
}

export const HomeSetup: React.FC<HomeSetupProps> = ({ onInitialized }) => {
  const [loading, setLoading] = useState(false);
  const [directoryStatus, setDirectoryStatus] = useState<any>(null);
  const [checkingDirectory, setCheckingDirectory] = useState(false);
  const [setupForm, setSetupForm] = useState<SetupFormData>({
    home_directory: `/Users/${window.location.hostname === 'localhost' ? 'maxim' : 'user'}/devteam-home`,
    primary_folder: '',
    anthropic_api_key: '',
    github_token: '',
    telegram_bot_token: '',
    telegram_channel_id: ''
  });
  const [setupError, setSetupError] = useState<string>('');

  const checkDirectory = async (path: string) => {
    if (!path || path.length < 3) {
      setDirectoryStatus(null);
      return;
    }
    
    setCheckingDirectory(true);
    try {
      const response = await api.post('/workspace/check-directory', path);
      setDirectoryStatus(response.data);
    } catch (error) {
      setDirectoryStatus(null);
    } finally {
      setCheckingDirectory(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSetupForm(prev => ({
      ...prev,
      [name]: value
    }));
    
    if (name === 'home_directory' && value) {
      checkDirectory(value);
    }
  };

  const handleSetupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSetupError('');
    setLoading(true);

    try {
      await api.post('/app/initialize', setupForm);
      onInitialized();
    } catch (error: any) {
      setSetupError(error.response?.data?.detail || 'Failed to initialize application');
    } finally {
      setLoading(false);
    }
  };

  const getDirectoryStatusIcon = () => {
    if (checkingDirectory) {
      return <CircularProgress size={20} />;
    }
    
    if (!directoryStatus) {
      return null;
    }
    
    if (directoryStatus.exists && directoryStatus.is_directory && directoryStatus.writable) {
      return <CheckCircleIcon color="success" />;
    } else if (!directoryStatus.exists && directoryStatus.writable) {
      return <WarningIcon color="warning" />;
    } else {
      return <ErrorIcon color="error" />;
    }
  };

  const getDirectoryStatusMessage = () => {
    if (!directoryStatus || checkingDirectory) {
      return null;
    }
    
    if (directoryStatus.exists && directoryStatus.is_directory && directoryStatus.writable) {
      return <Typography variant="caption" color="success.main">Directory exists and is writable</Typography>;
    } else if (!directoryStatus.exists && directoryStatus.writable) {
      return <Typography variant="caption" color="warning.main">Directory will be created</Typography>;
    } else if (!directoryStatus.writable) {
      return <Typography variant="caption" color="error.main">No write permission</Typography>;
    } else if (directoryStatus.exists && !directoryStatus.is_directory) {
      return <Typography variant="caption" color="error.main">Path exists but is not a directory</Typography>;
    }
    
    return null;
  };

  return (
    <Box 
      display="flex" 
      justifyContent="center" 
      alignItems="center" 
      minHeight="100vh"
      bgcolor="background.default"
    >
      <Paper sx={{ p: 4, maxWidth: 600, width: '100%' }}>
        <Box display="flex" alignItems="center" mb={3}>
          <FolderIcon sx={{ fontSize: 40, mr: 2, color: 'primary.main' }} />
          <Typography variant="h4">Welcome to DevTeam</Typography>
        </Box>
        
        <Typography variant="body1" color="text.secondary" mb={3}>
          Choose a home directory where DevTeam will store all your projects and configurations.
        </Typography>

        <form onSubmit={handleSetupSubmit}>
          <Stack spacing={3}>
            <TextField
              fullWidth
              label="Home Directory"
              name="home_directory"
              value={setupForm.home_directory}
              onChange={handleInputChange}
              required
              helperText={getDirectoryStatusMessage() || "This will be your DevTeam home directory"}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    {getDirectoryStatusIcon()}
                  </InputAdornment>
                )
              }}
            />
            
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Button
                size="small"
                variant="outlined"
                onClick={() => {
                  const path = `/Users/${window.location.hostname === 'localhost' ? 'maxim' : 'user'}/devteam-home`;
                  setSetupForm(prev => ({ ...prev, home_directory: path }));
                  checkDirectory(path);
                }}
              >
                Home Directory
              </Button>
              <Button
                size="small"
                variant="outlined"
                onClick={() => {
                  const path = `/Users/${window.location.hostname === 'localhost' ? 'maxim' : 'user'}/Documents/devteam-home`;
                  setSetupForm(prev => ({ ...prev, home_directory: path }));
                  checkDirectory(path);
                }}
              >
                Documents
              </Button>
              <Button
                size="small"
                variant="outlined"
                onClick={() => {
                  const path = `/Users/${window.location.hostname === 'localhost' ? 'maxim' : 'user'}/Desktop/devteam-home`;
                  setSetupForm(prev => ({ ...prev, home_directory: path }));
                  checkDirectory(path);
                }}
              >
                Desktop
              </Button>
            </Box>

            <TextField
              fullWidth
              label="Primary Folder (Optional)"
              name="primary_folder"
              value={setupForm.primary_folder}
              onChange={handleInputChange}
              helperText="Override location for all projects (leave empty to use home directory)"
            />

            <Typography variant="h6" mt={2}>API Keys</Typography>
            
            <TextField
              fullWidth
              label="Anthropic API Key"
              name="anthropic_api_key"
              type="password"
              value={setupForm.anthropic_api_key}
              onChange={handleInputChange}
              required
              helperText="Required for AI agents"
            />

            <TextField
              fullWidth
              label="GitHub Token (Optional)"
              name="github_token"
              type="password"
              value={setupForm.github_token}
              onChange={handleInputChange}
              helperText="For GitHub integration"
            />

            <TextField
              fullWidth
              label="Telegram Bot Token (Optional)"
              name="telegram_bot_token"
              type="password"
              value={setupForm.telegram_bot_token}
              onChange={handleInputChange}
              helperText="For Telegram notifications"
            />

            <TextField
              fullWidth
              label="Telegram Channel ID (Optional)"
              name="telegram_channel_id"
              value={setupForm.telegram_channel_id}
              onChange={handleInputChange}
              helperText="Channel ID for notifications"
            />

            {setupError && (
              <Alert severity="error">{setupError}</Alert>
            )}

            <Button
              type="submit"
              variant="contained"
              size="large"
              fullWidth
              disabled={loading || (directoryStatus && !directoryStatus.writable)}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              {loading ? 'Initializing...' : 'Initialize DevTeam'}
            </Button>
          </Stack>
        </form>
      </Paper>
    </Box>
  );
};