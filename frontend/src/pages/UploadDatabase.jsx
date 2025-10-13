import React from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function UploadDatabase({ token }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [modelName, setModelName] = useState("");
  const [purpose, setPurpose] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!file) { setError("Select a file"); return; }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", name);
    formData.append("description", description);
    formData.append("model_name", modelName);
    formData.append("purpose", purpose);
    formData.append("user_id", 1);

    try {
      const res = await fetch("http://127.0.0.1:5001/databases/databases/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        navigate("/databases");
      } else {
        setError(data.error || JSON.stringify(data));
      }
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="max-w-md mx-auto p-4 border mt-4">
      <h2 className="text-lg mb-4">Upload Database</h2>
      {error && <p className="text-red-500">{error}</p>}
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <input type="text" placeholder="Name" value={name} onChange={e => setName(e.target.value)} className="border p-2 rounded" required />
        <input type="text" placeholder="Description" value={description} onChange={e => setDescription(e.target.value)} className="border p-2 rounded" required />
        <input type="text" placeholder="Model Name" value={modelName} onChange={e => setModelName(e.target.value)} className="border p-2 rounded" required />
        <input type="text" placeholder="Purpose" value={purpose} onChange={e => setPurpose(e.target.value)} className="border p-2 rounded" required />
        <input type="file" onChange={e => setFile(e.target.files[0])} className="border p-2 rounded" required />
        <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded mt-2">Upload</button>
      </form>
    </div>
  );
}
