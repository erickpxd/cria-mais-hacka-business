import React from 'react';

const LanguageSelector = ({ selectedLanguage, onChange }) => {
  const languages = [
    { code: 'en', name: 'English' },
    { code: 'pt', name: 'Português' },
    { code: 'es', name: 'Español' },
    { code: 'fr', name: 'Français' },
    { code: 'de', name: 'Deutsch' },
  ];

  return (
    <div style={{ margin: '15px 0' }}>
      <label htmlFor="lang-select" style={{ marginRight: '10px', fontWeight: 'bold' }}>
        Translate to:
      </label>
      <select 
        id="lang-select"
        value={selectedLanguage} 
        onChange={(e) => onChange(e.target.value)}
        style={{ padding: '5px 10px', borderRadius: '4px', cursor: 'pointer' }}
      >
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.name}
          </option>
        ))}
      </select>
    </div>
  );
};

export default LanguageSelector;