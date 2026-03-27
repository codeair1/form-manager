import React, { useState } from 'react';

function App() {
  // Navigation state: 'home', 'builder', or 'scanner'
  const [view, setView] = useState('home');
  const [formName, setFormName] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
const [scanResult, setScanResult] = useState(null);
  const [data, setData] = useState([
    { question: "How was the service?", options: ["Good", "Average", "Bad"] }
  ]);
  const [loading, setLoading] = useState(false);

  // --- Logic Functions ---
  const handleStartCreation = () => {
    const name = prompt("Please enter a name for your OMR Form:");
    if (name && name.trim() !== "") {
      setFormName(name);
      setView('builder');
    } else if (name !== null) {
      alert("Form name is required to start.");
    }
  };

  // --- OMR Builder Functions (Add/Remove/Update) ---
  const addQuestion = () => setData([...data, { question: "", options: [""] }]);
  const removeQuestion = (qIndex) => setData(data.filter((_, index) => index !== qIndex));
  const updateQuestion = (index, value) => {
    const newData = [...data];
    newData[index].question = value;
    setData(newData);
  };
  const addOption = (qIndex) => {
    const newData = [...data];
    newData[qIndex].options.push("");
    setData(newData);
  };
  const removeLastOption = (qIndex) => {
    const newData = [...data];
    if (newData[qIndex].options.length > 1) {
      newData[qIndex].options.pop();
      setData(newData);
    }
  };
  const updateOption = (qIndex, oIndex, value) => {
    const newData = [...data];
    newData[qIndex].options[oIndex] = value;
    setData(newData);
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/new_form', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ survey_data: data, form_name: formName }),
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${formName.replace(/\s+/g, '_')}.pdf`;
        a.click();
      }
    } catch (error) {
      alert("Connection error.");
    } finally {
      setLoading(false);
    }
  };

  // --- Views ---

  // 1. HOME VIEW
  if (view === 'home') {
    return (
      <div style={{ 
        height: '100vh', display: 'flex', flexDirection: 'column', 
        justifyContent: 'center', alignItems: 'center', backgroundColor: '#f4f4f9', fontFamily: 'Arial' 
      }}>
        <h1 style={{ fontSize: '3rem', color: '#333', marginBottom: '1rem' }}>OMR System</h1>
        <p style={{ color: '#666', marginBottom: '2rem' }}>Create professional forms or process results.</p>
        
        <div style={{ display: 'flex', gap: '20px' }}>
            <button 
              onClick={handleStartCreation}
              style={{ 
                padding: '15px 40px', fontSize: '1.1rem', backgroundColor: '#28a745', 
                color: 'white', border: 'none', borderRadius: '50px', cursor: 'pointer', boxShadow: '0 4px 15px rgba(40, 167, 69, 0.3)'
              }}
            >
              Create New Form
            </button>

            <button 
              onClick={() => setView('scanner')}
              style={{ 
                padding: '15px 40px', fontSize: '1.1rem', backgroundColor: '#007bff', 
                color: 'white', border: 'none', borderRadius: '50px', cursor: 'pointer', boxShadow: '0 4px 15px rgba(0, 123, 255, 0.3)'
              }}
            >
              Scan Feedbacks
            </button>
        </div>
      </div>
    );
  }

  // 2. SCANNER VIEW (Placeholder for your OCR logic)
// --- Scanner Logic ---


const handleUpload = async () => {
  if (!selectedFile) return alert("Please select an image first!");
  
  setLoading(true);
  const formData = new FormData();
  formData.append('image', selectedFile);

  try {
    const response = await fetch('http://localhost:8000/api/upload', {
      method: 'POST',
      body: formData, // No headers needed, browser sets content-type for FormData
    });

    const result = await response.json();
    setScanResult(result);
    console.log("OCR Result:", result);
  } catch (error) {
    console.error("Upload Error:", error);
    alert("Failed to connect to scanner API.");
  } finally {
    setLoading(false);
  }
};

if (view === 'scanner') {
  return (
    <div style={{ padding: '40px', fontFamily: 'Arial', backgroundColor: '#f4f4f9', minHeight: '100vh' }}>
      <div style={{ maxWidth: '600px', margin: 'auto', backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        <button onClick={() => {setView('home'); setScanResult(null);}} style={{ marginBottom: '20px', cursor: 'pointer' }}>← Back to Home</button>
        <h2 style={{ textAlign: 'center', color: '#333' }}>Feedback Scanner</h2>
        
        <div style={{ border: '2px dashed #007bff', padding: '30px', borderRadius: '10px', textAlign: 'center', backgroundColor: '#f8fbff' }}>
          <input 
            type="file" 
            accept="image/*" 
            onChange={(e) => setSelectedFile(e.target.files[0])}
            style={{ marginBottom: '20px' }}
          />
          <br />
          <button 
            onClick={handleUpload}
            disabled={loading}
            style={{ 
              padding: '10px 25px', backgroundColor: loading ? '#ccc' : '#007bff', 
              color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' 
            }}
          >
            {loading ? "Processing..." : "Upload & Scan OMR"}
          </button>
        </div>

        {scanResult && (
          <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#e9ecef', borderRadius: '5px' }}>
            <h3>Scan Results:</h3>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem' }}>
              {JSON.stringify(scanResult, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

  // 3. BUILDER VIEW (Original logic)
  return (
    <div style={{ padding: '40px', fontFamily: 'Arial', backgroundColor: '#f4f4f9', minHeight: '100vh' }}>
      <div style={{ maxWidth: '700px', margin: 'auto', backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <button onClick={() => setView('home')} style={{ background: 'none', border: '1px solid #ccc', cursor: 'pointer', padding: '5px 10px', borderRadius: '4px' }}>← Back</button>
            <h2 style={{ margin: 0, color: '#333' }}>Editing: {formName}</h2>
            <div style={{ width: '60px' }}></div> 
        </div>
        
        {data.map((q, qIndex) => (
          <div key={qIndex} style={{ border: '1px solid #ddd', padding: '15px', borderRadius: '5px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong>Question {qIndex + 1}</strong>
              <button onClick={() => removeQuestion(qIndex)} style={{ color: 'red', border: 'none', background: 'none', cursor: 'pointer' }}>Delete</button>
            </div>
            
            <input 
              placeholder="Input Question Here"
              value={q.question}
              onChange={(e) => updateQuestion(qIndex, e.target.value)}
              style={{ width: '100%', padding: '8px', marginTop: '10px', marginBottom: '10px', boxSizing: 'border-box' }}
            />

            <div style={{ marginLeft: '20px' }}>
              {q.options.map((opt, oIndex) => (
                <input 
                  key={oIndex}
                  placeholder={`Option ${oIndex + 1}`}
                  value={opt}
                  onChange={(e) => updateOption(qIndex, oIndex, e.target.value)}
                  style={{ width: '80%', padding: '6px', marginBottom: '5px', display: 'block' }}
                />
              ))}
              <div style={{ marginTop: '10px' }}>
                <button onClick={() => addOption(qIndex)}>+ Add Option</button>
                <button onClick={() => removeLastOption(qIndex)} style={{ marginLeft: '10px' }}>- Remove Last</button>
              </div>
            </div>
          </div>
        ))}

        <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
          <button onClick={addQuestion} style={{ flex: 1, padding: '10px' }}>Add New Question</button>
          <button 
            onClick={handleSubmit} 
            disabled={loading}
            style={{ flex: 1, padding: '10px', backgroundColor: loading ? '#ccc' : '#28a745', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            {loading ? "Generating..." : "Generate PDF"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;