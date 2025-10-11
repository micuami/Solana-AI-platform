#!/usr/bin/env node
/**
 * rent_model.js
 * Usage:
 *   node rent_model.js <model_hash_hex>
 * Env/optional args:
 *   WALLET_PATH  - path to keypair json (default: ~/.config/solana/id.json)
 *   PROGRAM_ID   - program id (default: inferred from Anchor.toml or REQUIRED)
 *   RPC_URL      - RPC url (default: http://127.0.0.1:8899)
 *   IDL_PATH     - idl json path (default: ../target/idl/blockchain.json)
 *
 * Example:
 *   PROGRAM_ID=GdRo... RPC_URL=http://127.0.0.1:8899 \
 *   WALLET_PATH=~/.config/solana/id.json \
 *   node rent_model.js 9f12...
 */

import fs from "fs";
import path from "path";
import toml from "toml";
import * as anchor from "@project-serum/anchor";
import { Connection, Keypair, PublicKey, SystemProgram } from "@solana/web3.js";

function exitJSON(obj, code = 0) {
  console.log(JSON.stringify(obj));
  process.exit(code);
}

function expandHome(p) {
  if (!p) return p;
  if (p.startsWith("~/")) return path.join(process.env.HOME || process.env.USERPROFILE || "~", p.slice(2));
  return p;
}

function readKeypairFromFile(filePath) {
  const raw = fs.readFileSync(filePath, "utf8");
  const arr = JSON.parse(raw);
  return Keypair.fromSecretKey(Uint8Array.from(arr));
}

function loadAnchorToml(tomlPath) {
  try {
    const txt = fs.readFileSync(tomlPath, "utf8");
    return toml.parse(txt);
  } catch (e) {
    return null;
  }
}

async function inferProgramIdFromAnchorToml() {
  const candPaths = [
    path.join(process.cwd(), "..", "Anchor.toml"),
    path.join(process.cwd(), "..", "..", "Anchor.toml"),
    path.join(process.cwd(), "Anchor.toml"),
  ];
  for (const p of candPaths) {
    if (fs.existsSync(p)) {
      const parsed = loadAnchorToml(p);
      if (parsed && parsed.programs) {
        const envs = Object.keys(parsed.programs);
        for (const env of envs) {
          const programs = parsed.programs[env];
          const names = Object.keys(programs);
          if (names.length > 0 && programs[names[0]]) {
            return programs[names[0]];
          }
        }
      }
    }
  }
  return null;
}

async function main() {
  try {
    const argv = process.argv.slice(2);
    if (argv.length < 1) {
      exitJSON({ success: false, error: "Usage: rent_model.js <model_hash_hex>" }, 1);
    }

    const [modelHashHex] = argv;

    // defaults and envs
    const walletPathArg = process.env.WALLET_PATH || process.env.SOLANA_WALLET || "~/.config/solana/id.json";
    const walletPath = expandHome(walletPathArg);
    let programIdArg = process.env.PROGRAM_ID || null;
    const rpcUrl = process.env.RPC_URL || "http://127.0.0.1:8899";
    const idlPathEnv = process.env.IDL_PATH || path.join(process.cwd(), "..", "target", "idl", "blockchain.json");

    if (!/^[0-9a-fA-F]{64}$/.test(modelHashHex)) {
      exitJSON({ success: false, error: "model_hash_hex must be 64 hex chars (sha256 hex)" }, 1);
    }

    // wallet
    if (!fs.existsSync(walletPath)) {
      exitJSON({ success: false, error: `wallet file not found: ${walletPath}` }, 1);
    }
    const keypair = readKeypairFromFile(walletPath);

    // IDL
    let idlPath = idlPathEnv;
    if (!fs.existsSync(idlPath)) {
      const alt = path.join(process.cwd(), "target", "idl", "blockchain.json");
      if (fs.existsSync(alt)) idlPath = alt;
    }
    if (!fs.existsSync(idlPath)) {
      exitJSON({ success: false, error: `IDL file not found at ${idlPath}. Set IDL_PATH env or ensure Anchor build run.` }, 1);
    }
    const idl = JSON.parse(fs.readFileSync(idlPath, "utf8"));

    // program id
    let programId = programIdArg;
    if (!programId) {
      programId = await inferProgramIdFromAnchorToml();
    }
    if (!programId) {
      exitJSON({ success: false, error: "program_id not provided and couldn't be inferred. Set PROGRAM_ID env or pass as arg." }, 1);
    }

    // Setup provider
    const programPubkey = new PublicKey(programId);
    const connection = new Connection(rpcUrl, "confirmed");
    const wallet = new anchor.Wallet(keypair);
    const provider = new anchor.AnchorProvider(connection, wallet, anchor.AnchorProvider.defaultOptions());
    anchor.setProvider(provider);

    const program = new anchor.Program(idl, programPubkey, provider);

    // derive PDA: seeds = ["model", model_hash_bytes]
    const seedBytes = Buffer.from(modelHashHex, "hex");
    if (seedBytes.length !== 32) {
      exitJSON({ success: false, error: "model_hash_hex must be 32 bytes (64 hex chars)" }, 1);
    }
    const [modelPda] = await PublicKey.findProgramAddress([Buffer.from("model"), seedBytes], program.programId);

    // fetch model account to ensure exists and get uploader pubkey
    let modelAccount;
    try {
      modelAccount = await program.account.model.fetch(modelPda);
    } catch (e) {
      exitJSON({ success: false, error: "Model account not found on-chain for given hash", details: e.message || String(e) }, 1);
    }

    // uploader pubkey depends on your account layout; we expect a pubkey field named `uploader`
    let uploaderPubkey;
    try {
      uploaderPubkey = new PublicKey(modelAccount.uploader);
    } catch (e) {
      exitJSON({ success: false, error: "Failed to parse uploader pubkey from model account", details: e.message || String(e) }, 1);
    }

    // prepare args
    const modelHashArg = Array.from(seedBytes);

    // call rent_model
    const tx = await program.methods
      .rentModel(modelHashArg)
      .accounts({
        model: modelPda,
        renter: provider.wallet.publicKey,
        uploader: uploaderPubkey,
        systemProgram: SystemProgram.programId,
      })
      .rpc();

    exitJSON({
      success: true,
      txid: tx,
      model_pda: modelPda.toBase58(),
      renter: provider.wallet.publicKey.toBase58(),
      uploader: uploaderPubkey.toBase58(),
    }, 0);
  } catch (err) {
    exitJSON({ success: false, error: err.message || String(err), stack: err.stack }, 1);
  }
}

main();
