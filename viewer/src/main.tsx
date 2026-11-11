import React from 'react';
import { createRoot } from 'react-dom/client';
import { ResearchApp } from './research-app';
import './styles.css';
import './research.css';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ResearchApp />
  </React.StrictMode>,
);
