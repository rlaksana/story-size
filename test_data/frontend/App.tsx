import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@material-ui/core/styles';
import CssBaseline from '@material-ui/core/CssBaseline';
import Dashboard from './components/Dashboard';
import UserProfile from './components/UserProfile';
import { authApi, dashboardApi } from './services/api';

const App: React.FC = () => {
  const [darkMode, setDarkMode] = useState(false);
  const [user, setUser] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);

  const theme = createTheme({
    palette: {
      mode: darkMode ? 'dark' : 'light',
    },
  });

  useEffect(() => {
    // Initialize user session
    const initializeApp = async () => {
      try {
        const userResponse = await authApi.getCurrentUser();
        setUser(userResponse.data);

        const dashboardResponse = await dashboardApi.getDashboardData();
        setDashboardData(dashboardResponse.data);
      } catch (error) {
        console.error('Failed to initialize app:', error);
      }
    };

    initializeApp();
  }, []);

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <div className="App">
          <Routes>
            <Route
              path="/"
              element={
                <Dashboard
                  user={user}
                  dashboardData={dashboardData}
                  darkMode={darkMode}
                  toggleDarkMode={toggleDarkMode}
                />
              }
            />
            <Route
              path="/profile"
              element={
                <UserProfile
                  user={user}
                  setUser={setUser}
                />
              }
            />
          </Routes>
        </div>
      </Router>
    </ThemeProvider>
  );
};

export default App;