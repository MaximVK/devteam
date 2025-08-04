import React, { useState, useEffect } from 'react'
import { Link as RouterLink, useLocation, useParams } from 'react-router-dom'
import {
  AppBar,
  Box,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Divider,
  Chip,
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  Folder as FolderIcon,
  People as PeopleIcon,
  Assignment as AssignmentIcon,
  Code as CodeIcon,
  Settings as SettingsIcon,
  Menu as MenuIcon,
  Home as HomeIcon,
} from '@mui/icons-material'
import api from '../services/api'

const drawerWidth = 240

interface LayoutProps {
  children: React.ReactNode
}

interface ProjectInfo {
  id: string
  name: string
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const params = useParams()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [currentProject, setCurrentProject] = useState<ProjectInfo | null>(null)
  
  // Detect if we're in a project context
  const projectId = params.projectId || null
  const isInProjectContext = location.pathname.includes('/projects/') && projectId
  
  useEffect(() => {
    if (projectId) {
      loadProjectInfo(projectId)
    } else {
      setCurrentProject(null)
    }
  }, [projectId])
  
  const loadProjectInfo = async (id: string) => {
    try {
      const response = await api.get(`/app/projects/${id}`)
      setCurrentProject({ id, name: response.data.name })
    } catch (error) {
      console.error('Failed to load project info:', error)
    }
  }
  
  const globalMenuItems = [
    { text: 'Projects', icon: <FolderIcon />, path: '/projects' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
  ]
  
  const projectMenuItems = [
    { text: 'Overview', icon: <DashboardIcon />, path: `/projects/${projectId}` },
    { text: 'Agents', icon: <PeopleIcon />, path: `/projects/${projectId}/agents` },
    { text: 'Tasks', icon: <AssignmentIcon />, path: `/projects/${projectId}/tasks` },
  ]

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          DevTeam
        </Typography>
      </Toolbar>
      
      {currentProject && (
        <>
          <Box sx={{ px: 2, py: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Current Project
            </Typography>
            <Typography variant="subtitle1" noWrap>
              {currentProject.name}
            </Typography>
          </Box>
          <Divider />
        </>
      )}
      
      <List>
        {/* Global Menu Items */}
        {globalMenuItems.map((item) => (
          <ListItem
            key={item.text}
            component={RouterLink}
            to={item.path}
            selected={location.pathname === item.path}
            sx={{
              backgroundColor: location.pathname === item.path ? '#e3f2fd' : 'transparent',
              '&:hover': {
                backgroundColor: '#f5f5f5',
              },
              '& .MuiListItemIcon-root': {
                color: location.pathname === item.path ? '#1976d2' : '#757575',
              },
              '& .MuiListItemText-primary': {
                color: location.pathname === item.path ? '#1976d2' : '#424242',
              },
            }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItem>
        ))}
        
        {/* Project-specific Menu Items */}
        {isInProjectContext && (
          <>
            <Divider sx={{ my: 1 }} />
            <ListItem>
              <Typography variant="caption" color="text.secondary">
                Project Menu
              </Typography>
            </ListItem>
            {projectMenuItems.map((item) => (
              <ListItem
                key={item.text}
                component={RouterLink}
                to={item.path}
                selected={location.pathname === item.path}
                sx={{
                  backgroundColor: location.pathname === item.path ? '#e3f2fd' : 'transparent',
                  '&:hover': {
                    backgroundColor: '#f5f5f5',
                  },
                  '& .MuiListItemIcon-root': {
                    color: location.pathname === item.path ? '#1976d2' : '#757575',
                  },
                  '& .MuiListItemText-primary': {
                    color: location.pathname === item.path ? '#1976d2' : '#424242',
                  },
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItem>
            ))}
          </>
        )}
      </List>
    </div>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {currentProject ? `DevTeam - ${currentProject.name}` : 'DevTeam - Multi-Agent Development System'}
          </Typography>
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              backgroundColor: '#fafafa',
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              backgroundColor: '#fafafa',
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
        }}
      >
        <Toolbar />
        {children}
      </Box>
    </Box>
  )
}