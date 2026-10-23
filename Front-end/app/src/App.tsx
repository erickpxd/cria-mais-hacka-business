import {  useState, useRef } from 'react'
import { Link, Routes, Route } from 'react-router-dom';
import ImageUploader from './components/FileLoader.tsx'
import LanguageSelector from './components/LanguageSelector.tsx';
import './App.css'
import About from './About.tsx';

function App() {

  

  
  const [loading, setLoading] = useState<boolean>(false);
  
  const uploadToServer = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    try{
      const response = await fetch(`/api/upload?}`, {
        method: 'POST',
        body: formData,
      });

      if(response.ok){
        const data = await response.json();
        console.log("Success:", data);
        
      }
    } catch(error) {
      console.error("Upload failed:", error);
    }
  };

  return (
    <div>

      <h1>Análise de imagem</h1>
      <div>
        
        
        

      </div>
      <div>
        <ImageUploader onUpload={uploadToServer}/>
        
        {loading && <p>Processing image and translating...</p>}
      </div>
      <div>

        
      </div>
    </div>
  )
}

export default App
