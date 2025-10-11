#!/usr/bin/env node
// register_model.js
// Usage: node register_model.js <model_hash_hex> <storage_uri> <price_lamports> [wallet_path] [program_id] [rpc_url] [idl_path]
// Example:
// node register_model.js 9f12... "ipfs://CID" 1000000 ~/.config/solana/id.json "PROGRAM_PUBKEY" "https://api.devnet.solana.com" "../target/idl/solana_ai_platform.json"

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
    if (argv.length < 3) {
      exitJSON({ success: false, error: "Usage: register_model.js <model_hash_hex> <storage_uri> <price_lamports> [wallet_path] [program_id] [rpc_url] [idl_path]" }, 1);
    }

    const [modelHashHex, storageUri, priceLamportsStr] = argv;
    const walletPath = argv[3] || process.env.WALLET_PATH || process.env.SOLANA_WALLET || path.join(process.env.HOME || "~", ".config/solana/id.json");
    const programIdArg = argv[4] || process.env.PROGRAM_ID;
    const rpcUrl = argv[5] || process.env.RPC_URL || "https://api.devnet.solana.com";
    const idlPath = argv[6] || process.env.IDL_PATH || path.join(process.cwd(), "..", "target", "idl", "solana_ai_platform.json");

    if (!/^[0-9a-fA-F]{64}$/.test(modelHashHex)) {
      exitJSON({ success: false, error: "model_hash_hex must be 64 hex chars (sha256 hex)" }, 1);
    }

    const priceLamports = parseInt(priceLamportsStr, 10) || 0;

    // Load keypair
    if (!fs.existsSync(walletPath)) {
      exitJSON({ success: false, error: `wallet file not found: ${walletPath}` }, 1);
    }
    const keypair = readKeypairFromFile(walletPath);

    // Load IDL
    if (!fs.existsSync(idlPath)) {
      exitJSON({ success: false, error: `IDL file not found at ${idlPath}. Provide IDL_PATH or correct path.` }, 1);
    }
    const idl = JSON.parse(fs.readFileSync(idlPath, "utf8"));

    // Determine programId: from arg/env or try Anchor.toml (near idl)
    let programId = programIdArg;
    if (!programId) {
      // try to read Anchor.toml in parent folders
      const anchorTomlPaths = [
        path.join(process.cwd(), "..", "Anchor.toml"),
        path.join(process.cwd(), "..", "..", "Anchor.toml"),
        path.join(process.cwd(), "Anchor.toml"),
      ];
      for (const p of anchorTomlPaths) {
        if (fs.existsSync(p)) {
          const parsed = loadAnchorToml(p);
          if (parsed) {
            // find program id in parsed.toml programs -> localnet/devnet etc.
            if (parsed.programs) {
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
            if (programId) break;
          }
        }
      }
    }
    if (!programId) {
      exitJSON({ success: false, error: "program_id not provided and couldn't be inferred. Set PROGRAM_ID env or pass as arg." }, 1);
    }

    const programPubkey = new PublicKey(programId);

    // Setup provider
    const connection = new Connection(rpcUrl, "confirmed");
    const wallet = new anchor.Wallet(keypair);
    const provider = new anchor.AnchorProvider(connection, wallet, anchor.AnchorProvider.defaultOptions());
    anchor.setProvider(provider);

    const program = new anchor.Program(idl, programPubkey, provider);

    // derive PDA: seeds = ["model", model_hash_bytes]
    const seedBytes = Buffer.from(modelHashHex, "hex");
    const [modelPda, bump] = await PublicKey.findProgramAddress([Buffer.from("model"), seedBytes], program.programId);

    // prepare args: Anchor expects [u8;32] as Array<number>
    const modelHashArg = Array.from(seedBytes); // length 32
    const merkleRootArg = Array.from(Buffer.alloc(32, 0)); // zeros if not provided

    // call create_model
    const tx = await program.methods
      .createModel(modelHashArg, merkleRootArg, storageUri, new anchor.BN(priceLamports))
      .accounts({
        model: modelPda,
        uploader: provider.wallet.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .rpc();

    exitJSON({
      success: true,
      txid: tx,
      model_pda: modelPda.toBase58(),
      program_id: program.programId.toBase58(),
      wallet: provider.wallet.publicKey.toBase58(),
    }, 0);
  } catch (err) {
    // Print a clean JSON error
    exitJSON({ success: false, error: err.message || String(err), stack: err.stack }, 1);
  }
}

main();
