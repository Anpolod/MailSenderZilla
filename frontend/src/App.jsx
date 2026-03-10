import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import CampaignForm from './components/CampaignForm';
import CampaignDetail from './components/CampaignDetail';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/campaign/new" element={<CampaignForm />} />
          <Route path="/campaign/:id" element={<CampaignDetail />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
