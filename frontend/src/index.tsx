import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import { Agent13Intervention } from './components/Agent13Intervention';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <Agent13Intervention>
      <App />
    </Agent13Intervention>
  </React.StrictMode>
);