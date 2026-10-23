import React, { useState, useRef } from 'react';

const ImageUploader = ({onUpload}) => {
  const [image, setImage] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
      // Create a local URL for previewing the image
      setImage(URL.createObjectURL(file));
      onUpload(file);
    }
  };

  const triggerFileSelect = () => {
    // Manually click the hidden file input
    fileInputRef.current.click();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
      {/* 1. The hidden input */}
      <input
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        ref={fileInputRef}
        style={{ display: 'none' }}
      />

      {/* 2. The styled button that triggers the input */}
      <button 
        onClick={triggerFileSelect}
        style={{ padding: '10px 20px', cursor: 'pointer' }}
      >
        Upload Image
      </button>

      {/* 3. The Preview */}
      {image && (
        <div style={{ marginTop: '20px' }}>
          <p>Preview:</p>
          <img 
            src={image} 
            alt="Uploaded preview" 
            style={{ maxWidth: '300px', borderRadius: '10px' }} 
          />
        </div>
      )}
    </div>
  );
};

export default ImageUploader;