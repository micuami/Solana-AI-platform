use anchor_lang::prelude::*;

declare_id!("3Uxey2KwiZqMK2uTbqJBEqayjfo8jZFDEhZpU97RQVY6");

#[program]
pub mod blockchain {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        msg!("Greetings from: {:?}", ctx.program_id);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize {}
