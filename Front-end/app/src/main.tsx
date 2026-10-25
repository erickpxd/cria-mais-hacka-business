import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css';
import App from './App.tsx';
import About from './About.tsx';
import Handwriting from './Handwriting.tsx';

const style = {
  container: {
    fontFamily: '"Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    backgroundColor: '#f8f9fa',
    minHeight: '100vh',
    padding: '40px 20px',
    color: '#212529',
  },
  header: {
    textAlign: 'center' as const,
    marginBottom: '40px',
  },
  title: {
    fontSize: '2.5rem',
    fontWeight: '700',
    color: '#0d6efd',
    marginBottom: '10px',
  },
  subtitle: {
    fontSize: '1.1rem',
    color: '#6c757d',
  },
  content: {
    maxWidth: '800px',
    margin: '0 auto',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: '8px',
    padding: '25px',
    marginBottom: '20px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
    border: '1px solid #dee2e6',
  },
  sectionTitle: {
    fontSize: '1.25rem',
    fontWeight: '600',
    marginBottom: '15px',
    color: '#343a40',
  },
  text: {
    lineHeight: '1.6',
    fontSize: '1rem',
  },
  footer: {
    textAlign: 'center' as const,
    marginTop: '40px',
  },
  button: {
    display: 'inline-block',
    backgroundColor: '#0d6efd',
    color: '#fff',
    padding: '10px 25px',
    borderRadius: '5px',
    textDecoration: 'none',
    fontWeight: '500',
    transition: 'background-color 0.2s',
  },
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/about" element={<About />} />
        
        <Route path="/" element={<App />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
