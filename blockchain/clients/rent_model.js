#!/usr/bin/env node
// rent_model.js
// Usage: node rent_model.js <model_hash_hex> [renter_wallet_path] [program_id] [rpc_url] [idl_path]

import fs from "fs";
import path from "path";
import toml from "toml";
import * as anchor from "@project-serum/anchor";
import { Connection, Keypair, PublicKey, SystemProgram } from "@solana/web3.js";

function exitJSON(obj, code = 0) {
  console.log(JSON.stringify(obj));
  process.exit(code);
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

async function main() {
  try {
    const argv = process.argv.slice(2);
    if (argv.length < 1) {
      exitJSON({ success: false, error: "Usage: rent_model.js <model_hash_hex> [renter_wallet_path] [program_id] [rpc_url] [idl_path]" }, 1);
    }

    const [modelHashHex] = argv;
    const renterWalletPath = argv[1] || process.env.RENTER_WALLET || path.join(process.env.HOME || "~", ".config/solana/id.json");
    const programIdArg = argv[2] || process.env.PROGRAM_ID;
    const rpcUrl = argv[3] || process.env.RPC_URL || "https://api.devnet.solana.com";
    const idlPath = argv[4] || process.env.IDL_PATH || path.join(process.cwd(), "..", "target", "idl", "solana_ai_platform.json");

    if (!/^[0-9a-fA-F]{64}$/.test(modelHashHex)) {
      exitJSON({ success: false, error: "model_hash_hex must be 64 hex chars (sha256 hex)" }, 1);
    }

    if (!fs.existsSync(renterWalletPath)) {
      exitJSON({ success: false, error: `renter wallet not found: ${renterWalletPath}` }, 1);
    }
    const renterKeypair = readKeypairFromFile(renterWalletPath);

    if (!fs.existsSync(idlPath)) {
      exitJSON({ success: false, error: `IDL file not found at ${idlPath}` }, 1);
    }
    const idl = JSON.parse(fs.readFileSync(idlPath, "utf8"));

    let programId = programIdArg;
    if (!programId) {
      const anchorTomlPaths = [
        path.join(process.cwd(), "..", "Anchor.toml"),
        path.join(process.cwd(), "..", "..", "Anchor.toml"),
        path.join(process.cwd(), "Anchor.toml"),
      ];
      for (const p of anchorTomlPaths) {
        if (fs.existsSync(p)) {
          const parsed = loadAnchorToml(p);
          if (parsed && parsed.programs) {
            const envs = Object.keys(parsed.programs);
            for (const env of envs) {
              const programs = parsed.programs[env];
              const names = Object.keys(programs);
              if (names.length > 0) {
                programId = programs[names[0]];
                break;
              }
            }
          }
        }
        if (programId) break;
      }
    }
    if (!programId) {
      exitJSON({ success: false, error: "program_id not provided and couldn't be inferred. Set PROGRAM_ID env or pass as arg." }, 1);
    }

    const programPubkey = new PublicKey(programId);
    const connection = new Connection(rpcUrl, "confirmed");
    const wallet = new anchor.Wallet(renterKeypair);
    const provider = new anchor.AnchorProvider(connection, wallet, anchor.AnchorProvider.defaultOptions());
    anchor.setProvider(provider);

    const program = new anchor.Program(idl, programPubkey, provider);

    // derive PDA
    const seedBytes = Buffer.from(modelHashHex, "hex");
    const [modelPda] = await PublicKey.findProgramAddress([Buffer.from("model"), seedBytes], program.programId);

    // fetch model account to get uploader pubkey (account fields depend on your Anchor struct)
    let modelAccount;
    try {
      modelAccount = await program.account.model.fetch(modelPda);
    } catch (e) {
      exitJSON({ success: false, error: "Model account not found on-chain for given hash", details: e.message || String(e) }, 1);
    }

    const uploaderPubkey = new PublicKey(modelAccount.uploader);

    // need to pass array form of hash
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
