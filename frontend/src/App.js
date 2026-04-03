import React, { useState } from 'react';

function App() {
  const [view, setView] = useState('home');
  const [formName, setFormName] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [scanResult, setScanResult] = useState(null);
  const [data, setData] = useState([
    { question: "How was the service?", options: ["Good", "Average", "Bad"] }
  ]);
  const [loading, setLoading] = useState(false);

  // --- OMR Builder Functions ---
  const handleStartCreation = () => {
    const name = prompt("Please enter a name for your OMR Form:");
    if (name && name.trim() !== "") {
      setFormName(name);
      setView('builder');
    }
  };

  const addQuestion = () => setData([...data, { question: "", options: ["A", "B", "C", "D"] }]);
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

  // --- API: Generate PDF ---
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
      } else {
        alert("Failed to generate PDF.");
      }
    } catch (error) {
      alert("Connection error.");
    } finally {
      setLoading(false);
    }
  };

  // --- API: Scan OMR ---
  const handleUpload = async () => {
    if (!selectedFiles.length) return alert("Please select at least one image file.");
    setLoading(true);
  
    const formData = new FormData();
  
    selectedFiles.forEach(file => {
      const parts = file.webkitRelativePath.replace("\\", "/").split("/");
      const subFolder = parts.length >= 3 ? parts[parts.length - 2] : "root";
      const encodedName = `${subFolder}__${file.name}`;  // e.g. "1__page1.jpg"
      // ✅ Rename the file by creating a new File object with the encoded name
      const renamedFile = new File([file], encodedName, { type: file.type });
      formData.append('images', renamedFile);
      console.log(`Appending: ${encodedName}`);
    });
  
    try {
      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      });
      const result = await response.json();
      if (response.ok) {
        setScanResult(result.results?.[0]?.data || null);
        alert(`Upload Successful! ${result.successful}/${result.total_folders} folder(s) processed.`);
      } else {
        alert("Server Error: " + (result.error || result.message));
      }
    } catch (error) {
      alert("Network Error: Could not connect to Flask.");
    } finally {
      setLoading(false);
    }
  };

  // --- 1. HOME VIEW ---
  if (view === 'home') {
    return (
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', backgroundColor: '#f4f4f9', fontFamily: 'Arial' }}>
        <h1 style={{ fontSize: '3rem', color: '#333' }}>OMR System</h1>
        <div style={{ display: 'flex', gap: '20px' }}>
          <button onClick={handleStartCreation} style={{ padding: '15px 40px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '50px', cursor: 'pointer' }}>Create New Form</button>
          <button onClick={() => setView('scanner')} style={{ padding: '15px 40px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '50px', cursor: 'pointer' }}>Scan Feedbacks</button>
        </div>
      </div>
    );
  }

  // --- 2. SCANNER VIEW ---
  if (view === 'scanner') {
    return (
      <div style={{ padding: '40px', fontFamily: 'Arial', minHeight: '100vh', backgroundColor: '#f4f4f9' }}>
        <div style={{ maxWidth: '600px', margin: 'auto', backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>

          <button onClick={() => { setView('home'); setScanResult(null); setSelectedFiles([]); }} style={{ marginBottom: '20px' }}>← Back to Home</button>
          <h2 style={{ textAlign: 'center' }}>OMR Scanner</h2>

          <div style={{ border: '2px dashed #ccc', padding: '20px', textAlign: 'center', margin: '20px 0' }}>
            <input
              type="file"
              accept="image/*"
              webkitdirectory=""
              onChange={(e) => {
                const imageFiles = Array.from(e.target.files).filter(file =>
                  file.type.startsWith('image/')
                );
                // ✅ Attach relativePath directly onto each file object at selection time
                imageFiles.forEach(file => {
                  file._relativePath = file.webkitRelativePath || file.name;
                });
                setSelectedFiles(imageFiles);
                // Debug
                imageFiles.forEach(f => console.log(f.name, '|', f._relativePath));
              }}
            />
            {selectedFiles.length > 0 && (
              <p style={{ marginTop: '10px', color: '#555', fontSize: '0.85rem' }}>
                {selectedFiles.length} image(s) across{' '}
                <strong>
                  {/* ✅ Fixed: split('/') on "parentfolder/subfolder/file.jpg"
                      index -2 from end = subfolder name */}
                  {new Set(
                    selectedFiles
                      .map(f => f.webkitRelativePath.split('/'))
                      .filter(parts => parts.length >= 3)
                      .map(parts => parts[parts.length - 2])  // ✅ immediate parent subfolder
                  ).size}
                </strong>{' '}
                subfolder(s) detected
              </p>
            )}
          </div>

          <button
            onClick={handleUpload}
            disabled={loading}
            style={{ width: '100%', padding: '10px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            {loading ? "Processing..." : "Upload & Scan"}
          </button>

          {scanResult && (
            <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#e9ecef', borderRadius: '5px' }}>
              <h3>Results for: {scanResult.Full_name}</h3>
              <p><strong>Age:</strong> {scanResult.Age}</p>
              <p><strong>Contact:</strong> {scanResult.Contact_Number}</p>
              <p><strong>Gender:</strong> {scanResult.Gender}</p>
              <pre style={{ backgroundColor: '#fff', padding: '10px', borderRadius: '4px' }}>
                {JSON.stringify(scanResult.responses, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    );
  }

  // --- 3. BUILDER VIEW ---
  return (
    <div style={{ padding: '40px', fontFamily: 'Arial', backgroundColor: '#f4f4f9', minHeight: '100vh' }}>
      <div style={{ maxWidth: '700px', margin: 'auto', backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <button onClick={() => setView('home')}>← Back</button>
          <h2 style={{ margin: 0 }}>Editing: {formName}</h2>
          <div style={{ width: '50px' }}></div>
        </div>

        {data.map((q, qIndex) => (
          <div key={qIndex} style={{ border: '1px solid #ddd', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong>Question {qIndex + 1}</strong>
              <button onClick={() => removeQuestion(qIndex)} style={{ color: 'red', border: 'none', background: 'none', cursor: 'pointer' }}>Delete</button>
            </div>

            <input
              placeholder="Enter your question text"
              value={q.question}
              onChange={(e) => updateQuestion(qIndex, e.target.value)}
              style={{ width: '100%', padding: '10px', margin: '10px 0', borderRadius: '4px', border: '1px solid #ccc' }}
            />

            <div style={{ marginLeft: '20px' }}>
              {q.options.map((opt, oIndex) => (
                <input
                  key={oIndex}
                  placeholder={`Option ${String.fromCharCode(65 + oIndex)}`}
                  value={opt}
                  onChange={(e) => updateOption(qIndex, oIndex, e.target.value)}
                  style={{ width: '90%', padding: '8px', marginBottom: '8px', display: 'block' }}
                />
              ))}
              <button onClick={() => addOption(qIndex)} style={{ fontSize: '0.8rem' }}>+ Add Option</button>
              <button onClick={() => removeLastOption(qIndex)} style={{ fontSize: '0.8rem', marginLeft: '10px' }}>- Remove Last</button>
            </div>
          </div>
        ))}

        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={addQuestion} style={{ flex: 1, padding: '12px' }}>Add Question</button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            style={{ flex: 1, padding: '12px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            {loading ? "Generating PDF..." : "Generate PDF"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;