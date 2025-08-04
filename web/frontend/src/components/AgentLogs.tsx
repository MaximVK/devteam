import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  IconButton,
  CircularProgress,
  Alert,
  Paper
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import RefreshIcon from '@mui/icons-material/Refresh';
import api from '../services/api';

interface AgentLogsProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  agentId: string;
  agentName: string;
}

export const AgentLogs: React.FC<AgentLogsProps> = ({
  open,
  onClose,
  projectId,
  agentId,
  agentName
}) => {
  const [logs, setLogs] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [totalLines, setTotalLines] = useState(0);

  const loadLogs = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await api.get(
        `/app/projects/${projectId}/agents/${agentId}/logs?lines=500`
      );
      
      if (response.data.exists) {
        setLogs(response.data.content);
        setTotalLines(response.data.total_lines);
      } else {
        setError('Log file not found. The agent may not have started properly.');
        setLogs('');
      }
    } catch (err: any) {
      console.error('Failed to load logs:', err);
      setError(err.response?.data?.detail || 'Failed to load logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      loadLogs();
    }
  }, [open, projectId, agentId]);

  const handleRefresh = () => {
    loadLogs();
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: { height: '80vh' }
      }}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">
            Logs for {agentName}
          </Typography>
          <Box>
            <IconButton onClick={handleRefresh} disabled={loading}>
              <RefreshIcon />
            </IconButton>
            <IconButton onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {loading ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Alert severity="error">{error}</Alert>
        ) : (
          <Box>
            {totalLines > 0 && (
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                Showing last 500 lines of {totalLines} total
              </Typography>
            )}
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                bgcolor: '#1e1e1e',
                color: '#d4d4d4',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
                overflow: 'auto',
                maxHeight: 'calc(80vh - 200px)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}
            >
              {logs || 'No logs available'}
            </Paper>
          </Box>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};