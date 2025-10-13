import React from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function UploadModel({ token }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [price, setPrice] = useState(0);
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
    formData.append("price_lamports", price);
    formData.append("uploader_wallet_path", "~/.config/solana/id.json");

    try {
      const res = await fetch("http://127.0.0.1:5001/models/models/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        navigate("/models");
      } else {
        setError(data.error || JSON.stringify(data));
      }
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="max-w-md mx-auto p-4 border mt-4">
      <h2 className="text-lg mb-4">Upload Model</h2>
      {error && <p className="text-red-500">{error}</p>}
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <input type="text" placeholder="Name" value={name} onChange={e => setName(e.target.value)} className="border p-2 rounded" required />
        <input type="text" placeholder="Description" value={description} onChange={e => setDescription(e.target.value)} className="border p-2 rounded" required />
        <input type="number" placeholder="Price (lamports)" value={price} onChange={e => setPrice(e.target.value)} className="border p-2 rounded" required />
        <input type="file" onChange={e => setFile(e.target.files[0])} className="border p-2 rounded" required />
        <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded mt-2">Upload</button>
      </form>
    </div>
  );
}
