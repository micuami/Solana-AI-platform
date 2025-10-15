#!/usr/bin/env node
/**
 * register_model.js (ready-for-devnet)
 *
 * Usage:
 *   node register_model.js <model_hash_hex> <storage_uri> <price_lamports>
 *
 * Env vars:
 *   WALLET_PATH  - path to keypair json (default: ~/.config/solana/id.json)
 *   PROGRAM_ID   - Solana program id (fallback: idl.address)
 *   RPC_URL      - RPC url (default: https://api.devnet.solana.com)
 *   IDL_PATH     - path to IDL JSON (default: ../target/idl/model_registry.json)
 */

import 'dotenv/config';
import fs from "fs";
import path from "path";
import * as anchor from "@coral-xyz/anchor";
import BN from "bn.js";
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

async function main() {
  try {
    const argv = process.argv.slice(2);
    if (argv.length < 3) {
      exitJSON({ success: false, error: "Usage: register_model.js <model_hash_hex> <storage_uri> <price_lamports>" }, 1);
    }

    const [modelHashHex, storageUri, priceLamportsStr] = argv;
    if (!/^[0-9a-fA-F]{64}$/.test(modelHashHex)) {
      exitJSON({ success: false, error: "model_hash_hex must be 64 hex chars" }, 1);
    }
    const priceLamports = Number.parseInt(priceLamportsStr, 10) || 0;

    // Wallet
    const walletPath = expandHome(process.env.WALLET_PATH || "~/.config/solana/id.json");
    if (!fs.existsSync(walletPath)) {
      exitJSON({ success: false, error: `Wallet file not found: ${walletPath}` }, 1);
    }
    const keypair = readKeypairFromFile(walletPath);

    // IDL
    let idlPath = process.env.IDL_PATH || path.join(process.cwd(), "..", "target", "idl", "model_registry.json");
    if (!fs.existsSync(idlPath)) {
      exitJSON({ success: false, error: `IDL file not found: ${idlPath}` }, 1);
    }
    const idl = JSON.parse(fs.readFileSync(idlPath, "utf8"));

    console.log("Using IDL path:", idlPath);

    // Provider
    const connection = new Connection(process.env.RPC_URL || "https://api.devnet.solana.com", "confirmed");
    const wallet = new anchor.Wallet(keypair);
    const provider = new anchor.AnchorProvider(connection, wallet, anchor.AnchorProvider.defaultOptions());
    anchor.setProvider(provider);

    // Program
    const programPubkey = new PublicKey(process.env.PROGRAM_ID || idl.address);
    const program = new anchor.Program(idl, provider);

    console.log("program.id:", program.programId.toBase58());
    console.log("program.methods keys:", Object.keys(program.methods));

    // derive PDA
    const seedBytes = Buffer.from(modelHashHex, "hex");
    const [modelPda] = await PublicKey.findProgramAddress([Buffer.from("model"), seedBytes], program.programId);

    // prepare args
    const modelHashArg = Array.from(seedBytes);                 // [u8;32]
    const merkleRootArg = Array.from(Buffer.alloc(32, 0));     // [u8;32] zeros
    const storageUriArg = storageUri;                           // string
    const priceArg = new BN(priceLamports.toString());          // u64

    console.log("DEBUG ARGS:");
    console.log(" modelHashArg len:", modelHashArg.length);
    console.log(" merkleRootArg len:", merkleRootArg.length);
    console.log(" storageUri:", storageUriArg);
    console.log(" price:", priceArg.toString());

    // send transaction
    const txid = await program.methods
      .createModel(modelHashArg, merkleRootArg, storageUriArg, priceArg)
      .accounts({
        model: modelPda,
        uploader: provider.wallet.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .rpc();

    exitJSON({
      success: true,
      txid,
      model_pda: modelPda.toBase58(),
      program_id: program.programId.toBase58(),
      wallet: provider.wallet.publicKey.toBase58()
    }, 0);

  } catch (err) {
    exitJSON({ success: false, error: err.message || String(err), stack: err.stack }, 1);
  }
}

main();
