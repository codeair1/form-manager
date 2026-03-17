import { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);
  const [boxes, setBoxes] = useState([]); 

  const handleUpload = async () => {
    const formData = new FormData();
    formData.append("image", file);

    try {
      const res = await axios.post("/api/omr", formData);

      setBoxes(res.data.boxes); 

    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div>
      <h2>Upload Image</h2>

      <input
        type="file"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <button onClick={handleUpload}>Upload</button>

      <hr />

      <h3>OMR Output:</h3>
      {boxes.map((box, index) => (
        <p key={index}>
          Box {index + 1}: {box.checked ? "✅ Checked" : "❌ Empty"}
        </p>
      ))}
    </div>
  );
}

export default App;