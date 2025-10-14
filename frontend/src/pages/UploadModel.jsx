import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export default function UploadModel({ token }) {
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState(0);
  const [walletPath, setWalletPath] = useState("");
  const [status, setStatus] = useState("");
  const navigate = useNavigate();

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !name) {
      alert("File and name are required");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", name);
    formData.append("description", description);
    formData.append("price_lamports", price);
    if (walletPath) formData.append("uploader_wallet_path", walletPath);

    setStatus("Uploading...");

    try {
      const res = await axios.post(
        "http://127.0.0.1:5001/models/models/upload",
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "multipart/form-data",
          },
        }
      );
      setStatus(`Uploaded! On-chain tx: ${res.data.onchain_tx || "pending"}`);
      // redirect to models page after short delay
      setTimeout(() => navigate("/models"), 2000);
    } catch (err) {
      console.error(err);
      setStatus(`Upload failed: ${err.response?.data?.message || err.message}`);
    }
  };

  return (
    <div className="p-4 max-w-md mx-auto">
      <h2 className="text-lg font-semibold mb-4">Upload Model</h2>
      <form onSubmit={handleUpload} className="space-y-3">
        <div>
          <label className="block mb-1">File</label>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files[0])}
            className="border p-1 w-full"
          />
        </div>
        <div>
          <label className="block mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="border p-1 w-full"
            required
          />
        </div>
        <div>
          <label className="block mb-1">Description</label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="border p-1 w-full"
          />
        </div>
        <div>
          <label className="block mb-1">Price (lamports)</label>
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(Number(e.target.value))}
            className="border p-1 w-full"
          />
        </div>
        <div>
          <label className="block mb-1">Uploader Wallet Path (optional)</label>
          <input
            type="text"
            value={walletPath}
            onChange={(e) => setWalletPath(e.target.value)}
            className="border p-1 w-full"
          />
        </div>
        <button
          type="submit"
          className="bg-blue-600 text-white px-3 py-1 rounded"
        >
          Upload
        </button>
      </form>
      {status && <p className="mt-3 text-sm">{status}</p>}
    </div>
  );
}
