import React, { useState } from 'react';

const API = 'http://localhost:8000';

const btn = (color = '#007bff') => ({
  padding: '10px 24px',
  backgroundColor: color,
  color: 'white',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: '14px',
  fontWeight: '500',
});

const card = {
  backgroundColor: 'white',
  padding: '30px',
  borderRadius: '10px',
  boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
};

function App() {
  const [view, setView] = useState('home');

  // Builder state
  const [formName, setFormName] = useState('');
  const [data, setData] = useState([
    { question: "How was the service?", options: ["Good", "Average", "Bad"] }
  ]);
  const [loading, setLoading] = useState(false);

  // Scanner state
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [scanResult, setScanResult] = useState(null);

  // DB Viewer state
  const [dbFormName, setDbFormName] = useState('');
  const [dbRows, setDbRows] = useState([]);
  const [dbColumns, setDbColumns] = useState([]);
  const [dbError, setDbError] = useState('');

  // ── Builder Helpers ──────────────────────────────────────────────────────
  const handleStartCreation = () => {
    const name = prompt("Enter a name for your OMR Form:");
    if (name && name.trim()) { setFormName(name); setView('builder'); }
  };

  const addQuestion = () => setData([...data, { question: "", options: ["A", "B", "C", "D"] }]);
  const removeQuestion = (i) => setData(data.filter((_, idx) => idx !== i));
  const updateQuestion = (i, val) => { const d = [...data]; d[i].question = val; setData(d); };
  const addOption = (qi) => { const d = [...data]; d[qi].options.push(""); setData(d); };
  const removeLastOption = (qi) => { const d = [...data]; if (d[qi].options.length > 1) d[qi].options.pop(); setData(d); };
  const updateOption = (qi, oi, val) => { const d = [...data]; d[qi].options[oi] = val; setData(d); };

  // ── API: Generate PDF ────────────────────────────────────────────────────
  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/new_form`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ survey_data: data, form_name: formName }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `${formName.replace(/\s+/g, '_')}.pdf`; a.click();
      } else { alert("Failed to generate PDF."); }
    } catch { alert("Connection error."); }
    finally { setLoading(false); }
  };

  // ── API: Scan OMR ────────────────────────────────────────────────────────
  const handleUpload = async () => {
    if (!selectedFiles.length) return alert("Please select at least one image file.");
    setLoading(true);
    const formData = new FormData();
    selectedFiles.forEach(file => {
      const parts = file.webkitRelativePath.replace("\\", "/").split("/");
      const subFolder = parts.length >= 3 ? parts[parts.length - 2] : "root";
      const renamedFile = new File([file], `${subFolder}__${file.name}`, { type: file.type });
      formData.append('images', renamedFile);
    });
    try {
      const res = await fetch(`${API}/api/upload`, { method: 'POST', body: formData });
      const result = await res.json();
      if (res.ok) {
        setScanResult(result.results?.[0]?.data || null);
        alert(`Upload Successful! ${result.successful}/${result.total_folders} folder(s) processed.`);
      } else { alert("Server Error: " + (result.error || result.message)); }
    } catch { alert("Network Error: Could not connect to Flask."); }
    finally { setLoading(false); }
  };

  // ── Helper: Download Local CSV ──────────────────────────────────────────
  const handleDownloadCSV = () => {
    if (dbRows.length === 0) return;
    const headers = dbColumns.join(",");
    const identityCols = ['id', 'Full_name', 'Age', 'Contact_Number', 'Gender'];
    const csvRows = dbRows.map(row => {
      return dbColumns.map(col => {
        const val = identityCols.includes(col) ? (row[col] ?? '') : (row.responses?.[col] ?? '');
        const escaped = ('' + val).replace(/"/g, '""');
        return `"${escaped}"`;
      }).join(",");
    });
    const csvContent = [headers, ...csvRows].join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `${dbFormName}_data.csv`);
    link.click();
  };

  // ── API: Sync to Google Sheets ──────────────────────────────────────────
  // ── API: Fetch DB Rows ───────────────────────────────────────────────────
  const handleFetchDb = async () => {
    if (!dbFormName.trim()) return alert("Enter a form name.");
    setLoading(true); setDbRows([]); setDbColumns([]); setDbError('');
    try {
      const res = await fetch(`${API}/api/rows/${dbFormName.trim()}`);
      const result = await res.json();
      if (res.ok && result.rows?.length) {
        const allQKeys = [...new Set(
          result.rows.flatMap(r => Object.keys(r.responses || {}))
        )];

        const identityCols = ['id', 'Full_name', 'Age', 'Contact_Number', 'Gender'];
        setDbColumns([...identityCols, ...allQKeys]);
        setDbRows(result.rows);
      } else if (res.ok && result.rows?.length === 0) {
        setDbError('No rows found in this table.');
      } else {
        setDbError(result.error || 'Failed to fetch rows.');
      }
    } catch { setDbError("Connection error."); }
    finally { setLoading(false); }
  };

  // ═══════════════════════════════════════════════════════════════════════
  // HOME VIEW
  // ═══════════════════════════════════════════════════════════════════════
  if (view === 'home') return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', backgroundColor: '#f4f4f9', fontFamily: 'Arial', gap: '16px' }}>
      <h1 style={{ fontSize: '2.5rem', color: '#333', marginBottom: '8px' }}>OMR System</h1>
      <p style={{ color: '#777', marginBottom: '24px', fontSize: '15px' }}>Create forms, scan responses, and Download sheets</p>
      <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', justifyContent: 'center' }}>
        <button onClick={handleStartCreation} style={btn('#28a745')}>+ Create New Form</button>
        <button onClick={() => setView('scanner')} style={btn('#007bff')}>Scan Feedbacks</button>
        <button onClick={() => setView('db')} style={btn('#17a2b8')}>Download sheets</button>
      </div>
    </div>
  );

  // ═══════════════════════════════════════════════════════════════════════
  // SCANNER VIEW
  // ═══════════════════════════════════════════════════════════════════════
  if (view === 'scanner') return (
    <div style={{ padding: '40px', fontFamily: 'Arial', minHeight: '100vh', backgroundColor: '#f4f4f9' }}>
      <div style={{ maxWidth: '600px', margin: 'auto', ...card }}>
        <button onClick={() => { setView('home'); setScanResult(null); setSelectedFiles([]); }} style={{ marginBottom: '20px', background: 'none', border: 'none', cursor: 'pointer', color: '#555', fontSize: '14px' }}>← Back</button>
        <h2 style={{ textAlign: 'center', marginTop: 0 }}>OMR Scanner</h2>

        <div style={{ border: '2px dashed #ccc', padding: '20px', textAlign: 'center', borderRadius: '8px', margin: '20px 0' }}>
          <input
            type="file" accept="image/*" webkitdirectory=""
            onChange={(e) => {
              const imageFiles = Array.from(e.target.files).filter(f => f.type.startsWith('image/'));
              setSelectedFiles(imageFiles);
            }}
          />
          {selectedFiles.length > 0 && (
            <p style={{ marginTop: '10px', color: '#555', fontSize: '13px' }}>
              {selectedFiles.length} image(s) selected
            </p>
          )}
        </div>

        <button onClick={handleUpload} disabled={loading} style={{ ...btn('#007bff'), width: '100%' }}>
          {loading ? "Processing..." : "Upload & Scan"}
        </button>

        {scanResult && (
          <div style={{ marginTop: '20px', padding: '16px', backgroundColor: '#f0f4ff', borderRadius: '8px', border: '1px solid #d0dcff' }}>
            <h3 style={{ marginTop: 0 }}>Results: {scanResult.Full_name}</h3>

            <div style={{ display: 'flex', gap: '40px', marginBottom: '8px' }}>
              <p style={{ margin: 0 }}><strong>Age:</strong> {scanResult.Age || '—'}</p>
              <p style={{ margin: 0 }}><strong>Contact:</strong> {scanResult.Contact_Number || '—'}</p>
            </div>

            <p style={{ marginTop: 0 }}><strong>Gender:</strong> {scanResult.Gender}</p>
            <pre style={{ backgroundColor: 'white', padding: '12px', borderRadius: '6px', fontSize: '13px', overflowX: 'auto' }}>
              {JSON.stringify(scanResult.responses, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );

  // ═══════════════════════════════════════════════════════════════════════
  // Sheets download
  // ═══════════════════════════════════════════════════════════════════════
  if (view === 'db') return (
    <div style={{ padding: '40px', fontFamily: 'Arial', minHeight: '100vh', backgroundColor: '#f4f4f9' }}>
      <div style={{ maxWidth: '800px', margin: 'auto', ...card }}>
        <button onClick={() => { setView('home'); setDbFormName(''); setDbRows([]); setDbColumns([]); setDbError(''); }} style={{ marginBottom: '20px', background: 'none', border: 'none', cursor: 'pointer', color: '#555', fontSize: '14px' }}>← Back</button>
        <h2 style={{ textAlign: 'center', marginTop: 0 }}>Download Sheets</h2>

        <div style={{ marginBottom: '20px' }}>
          <input
            type="text"
            placeholder="Enter form name"
            value={dbFormName}
            onChange={(e) => setDbFormName(e.target.value)}
            style={{ width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #ccc', fontSize: '14px', boxSizing: 'border-box' }}
          />
        </div>

        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <button onClick={handleFetchDb} disabled={loading} style={{ ...btn('#007bff'), flex: 1 }}>
            {loading ? "Fetching..." : "Fetch Data"}
          </button>
          <button onClick={handleDownloadCSV} disabled={dbRows.length === 0} style={{ ...btn('#28a745'), flex: 1 }}>
            Download CSV
          </button>
        </div>

        {dbError && <p style={{ color: 'red', marginBottom: '20px' }}>{dbError}</p>}

        {dbRows.length > 0 && (
          <div style={{ marginTop: '20px' }}>
            <h3>Data Preview ({dbRows.length} rows)</h3>
            <div style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid #ddd', borderRadius: '5px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f8f9fa' }}>
                    {dbColumns.map(col => <th key={col} style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'left' }}>{col}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {dbRows.map((row, idx) => (
                    <tr key={idx}>
                      {dbColumns.map(col => {
                        const identityCols = ['id', 'Full_name', 'Age', 'Contact_Number', 'Gender'];
                        const val = identityCols.includes(col) ? (row[col] ?? '') : (row.responses?.[col] ?? '');
                        return <td key={col} style={{ padding: '8px', border: '1px solid #ddd' }}>{val}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  // ═══════════════════════════════════════════════════════════════════════
  // BUILDER VIEW
  // ═══════════════════════════════════════════════════════════════════════
  return (
    <div style={{ padding: '40px', fontFamily: 'Arial', backgroundColor: '#f4f4f9', minHeight: '100vh' }}>
      <div style={{ maxWidth: '700px', margin: 'auto', ...card }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <button onClick={() => setView('home')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#555', fontSize: '14px' }}>← Back</button>
          <h2 style={{ margin: 0, fontSize: '18px' }}>Editing: {formName}</h2>
          <div style={{ width: '60px' }} />
        </div>

        {data.map((q, qi) => (
          <div key={qi} style={{ border: '1px solid #e0e0e0', padding: '20px', borderRadius: '8px', marginBottom: '16px', backgroundColor: '#fafafa' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <strong style={{ fontSize: '14px', color: '#444' }}>Question {qi + 1}</strong>
              <button onClick={() => removeQuestion(qi)} style={{ color: '#dc3545', border: 'none', background: 'none', cursor: 'pointer', fontSize: '13px' }}>Delete</button>
            </div>
            <input
              placeholder="Enter your question text"
              value={q.question}
              onChange={e => updateQuestion(qi, e.target.value)}
              style={{ width: '100%', padding: '9px', borderRadius: '5px', border: '1px solid #ccc', fontSize: '14px', boxSizing: 'border-box', marginBottom: '10px' }}
            />
            <div style={{ marginLeft: '16px' }}>
              {q.options.map((opt, oi) => (
                <input
                  key={oi}
                  placeholder={`Option ${String.fromCharCode(65 + oi)}`}
                  value={opt}
                  onChange={e => updateOption(qi, oi, e.target.value)}
                  style={{ width: '90%', padding: '7px', marginBottom: '6px', display: 'block', borderRadius: '4px', border: '1px solid #ddd', fontSize: '13px' }}
                />
              ))}
              <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                <button onClick={() => addOption(qi)} style={{ fontSize: '12px', padding: '4px 10px', borderRadius: '4px', border: '1px solid #ccc', cursor: 'pointer', background: 'white' }}>+ Option</button>
                <button onClick={() => removeLastOption(qi)} style={{ fontSize: '12px', padding: '4px 10px', borderRadius: '4px', border: '1px solid #ccc', cursor: 'pointer', background: 'white' }}>- Remove Last</button>
              </div>
            </div>
          </div>
        ))}

        <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
          <button onClick={addQuestion} style={{ flex: 1, padding: '11px', borderRadius: '6px', border: '1px solid #ccc', cursor: 'pointer', background: 'white', fontSize: '14px' }}>+ Add Question</button>
          <button onClick={handleSubmit} disabled={loading} style={{ ...btn('#28a745'), flex: 1 }}>
            {loading ? "Generating..." : "Generate PDF"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;