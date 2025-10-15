use anchor_lang::prelude::*;
use anchor_lang::solana_program::{program::invoke, system_instruction};

declare_id!("ZSoUNwHGAwkCzCKkLEnkY1m3Ud7WUjQMWRh5p4LZfpT");

#[program]
pub mod model_registry {
    use super::*;

    pub fn create_model(
        ctx: Context<CreateModel>,
        model_hash: [u8; 32],
        merkle_root: [u8; 32],        
        storage_uri: String,
        price_lamports: u64,
    ) -> Result<()> {
        let model = &mut ctx.accounts.model;
        model.uploader = *ctx.accounts.uploader.key;
        model.model_hash = model_hash;
        model.merkle_root = merkle_root;
        model.merkle_present = true;
        model.storage_uri = storage_uri;
        model.price_lamports = price_lamports;
        model.timestamp = Clock::get()?.unix_timestamp;
        model.is_available = true;
        model.bump = ctx.bumps.model;
        model.times_rented = 0;

        emit!(ModelCreated {
            model: model.key(),
            uploader: model.uploader,
            price: price_lamports,
            timestamp: model.timestamp,
        });

        Ok(())
    }

    pub fn rent_model(ctx: Context<RentModel>) -> Result<()> {
        let model = &mut ctx.accounts.model;
        require!(model.is_available, ErrorCode::ModelNotAvailable);

        let renter = &ctx.accounts.renter;
        let uploader = &ctx.accounts.uploader;

        // Transfer SOL from renter -> uploader (CPI to system program)
        let ix = system_instruction::transfer(&renter.key(), &uploader.key(), model.price_lamports);
        invoke(
            &ix,
            &[
                renter.to_account_info(),
                uploader.to_account_info(),
                ctx.accounts.system_program.to_account_info(),
            ],
        )?;

        model.times_rented = model.times_rented.checked_add(1).ok_or(ErrorCode::MathOverflow)?;
        let now = Clock::get()?.unix_timestamp;
        emit!(ModelRented {
            model: model.key(),
            renter: renter.key(),
            amount: model.price_lamports,
            timestamp: now,
        });

        Ok(())
    }
}

#[derive(Accounts)]
#[instruction(model_hash: [u8; 32])]
pub struct CreateModel<'info> {
    /// PDA: seeds = ["model", model_hash]
    #[account(
        init,
        payer = uploader,
        space = ModelAccount::MAX_SIZE,
        seeds = [b"model", model_hash.as_ref()],
        bump
    )]
    pub model: Account<'info, ModelAccount>,

    #[account(mut)]
    pub uploader: Signer<'info>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(model_hash: [u8; 32])]
pub struct RentModel<'info> {
    /// model PDA (initialized previously)
    #[account(
        mut,
        seeds = [b"model", model_hash.as_ref()],
        bump = model.bump,
        has_one = uploader
    )]
    pub model: Account<'info, ModelAccount>,

    #[account(mut)]
    pub renter: Signer<'info>,

    /// CHECK: uploader account validated by has_one = uploader above
    #[account(mut)]
    pub uploader: SystemAccount<'info>,

    pub system_program: Program<'info, System>,
}

#[account]
pub struct ModelAccount {
    pub uploader: Pubkey,           // 32
    pub model_hash: [u8; 32],       // 32
    pub merkle_root: [u8; 32],      // 32
    pub merkle_present: bool,       // 1
    pub storage_uri: String,        // 4 + N (N = chosen max)
    pub price_lamports: u64,        // 8
    pub timestamp: i64,             // 8
    pub is_available: bool,         // 1
    pub bump: u8,                   // 1
    pub times_rented: u64,          // 8
    // + padding/reserved if vrei extindere
}

impl ModelAccount {
    // ajustează MAX_SIZE in funcție de lungimea maxima a URI-ului pe care o accepti
    // exemplu de calcul: 8 (discriminator) + 32 + 32 + 32 + 1 + (4 + 200) + 8 + 8 + 1 + 1 + 8 + padding
    pub const MAX_SIZE: usize = 8 + 32 + 32 + 32 + 1 + (4 + 200) + 8 + 8 + 1 + 1 + 8 + 32;
}

#[event]
pub struct ModelCreated {
    pub model: Pubkey,
    pub uploader: Pubkey,
    pub price: u64,
    pub timestamp: i64,
}

#[event]
pub struct ModelRented {
    pub model: Pubkey,
    pub renter: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
}

#[error_code]
pub enum ErrorCode {
    #[msg("Model is not available for rent")]
    ModelNotAvailable,
    #[msg("Math overflow")]
    MathOverflow,
}
