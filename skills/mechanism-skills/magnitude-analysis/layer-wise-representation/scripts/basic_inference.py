#!/usr/bin/env python3
"""
Basic TruthX Inference Example

This script demonstrates how to use the TruthX-enhanced Llama model for
generating truthful responses to questions.

Requirements:
- pip install torch transformers
- Download model from: https://huggingface.co/ICTNLP/Llama-2-7b-chat-TruthX
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import argparse
from typing import Optional, List


def load_truthx_model(model_name: str = "ICTNLP/Llama-2-7b-chat-TruthX"):
    """
    Load the TruthX-enhanced model and tokenizer.
    
    Args:
        model_name: Hugging Face model identifier or local path
        
    Returns:
        Tuple of (model, tokenizer)
    """
    print(f"Loading model: {model_name}")
    
    tokenizer = AutoTokenizer.from_pretrained(
        model_name, 
        trust_remote_code=True
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    # Move to CUDA if available
    if torch.cuda.is_available():
        model = model.cuda()
        print("Model loaded on CUDA")
    else:
        print("Model loaded on CPU")
    
    return model, tokenizer


def generate_response(
    model,
    tokenizer,
    prompt: str,
    max_length: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
    do_sample: bool = True
) -> str:
    """
    Generate a response using the TruthX model.
    
    Args:
        model: The loaded model
        tokenizer: The loaded tokenizer
        prompt: Input text prompt
        max_length: Maximum length of generated text
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        do_sample: Whether to use sampling
        
    Returns:
        Generated text response
    """
    # Encode the input
    encoded_inputs = tokenizer(prompt, return_tensors="pt")["input_ids"]
    
    # Move to same device as model
    if torch.cuda.is_available():
        encoded_inputs = encoded_inputs.cuda()
    
    # Generate response
    with torch.no_grad():
        outputs = model.generate(
            encoded_inputs,
            max_length=max_length,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            pad_token_id=tokenizer.eos_token_id
        )
    
    # Decode only the generated portion
    generated_tokens = outputs[0, encoded_inputs.shape[-1]:]
    response = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
    
    return response


def batch_generate(
    model,
    tokenizer,
    prompts: List[str],
    **kwargs
) -> List[str]:
    """
    Generate responses for multiple prompts.
    
    Args:
        model: The loaded model
        tokenizer: The loaded tokenizer
        prompts: List of input prompts
        **kwargs: Additional generation parameters
        
    Returns:
        List of generated responses
    """
    responses = []
    
    for i, prompt in enumerate(prompts):
        print(f"Processing prompt {i+1}/{len(prompts)}...")
        response = generate_response(model, tokenizer, prompt, **kwargs)
        responses.append(response)
    
    return responses


def interactive_mode(model, tokenizer):
    """
    Run an interactive chat session with the model.
    """
    print("\n=== Interactive TruthX Chat ===")
    print("Type 'quit' to exit\n")
    
    while True:
        # Get user input
        prompt = input("You: ").strip()
        
        if prompt.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not prompt:
            continue
        
        # Generate response
        response = generate_response(
            model, 
            tokenizer, 
            prompt,
            temperature=0.7,
            top_p=0.9
        )
        
        print(f"\nTruthX: {response}\n")


def main():
    parser = argparse.ArgumentParser(
        description="TruthX inference script for generating truthful responses"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="ICTNLP/Llama-2-7b-chat-TruthX",
        help="Path to TruthX model or Hugging Face identifier"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Single prompt to process"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=512,
        help="Maximum generation length"
    )
    
    args = parser.parse_args()
    
    # Load model
    model, tokenizer = load_truthx_model(args.model_path)
    
    if args.interactive:
        # Interactive mode
        interactive_mode(model, tokenizer)
    elif args.prompt:
        # Single prompt mode
        response = generate_response(
            model,
            tokenizer,
            args.prompt,
            max_length=args.max_length,
            temperature=args.temperature
        )
        print(f"\nPrompt: {args.prompt}")
        print(f"Response: {response}")
    else:
        # Demo with sample questions
        sample_questions = [
            "What are the benefits of eating an apple a day?",
            "What is the capital of France?",
            "Explain the theory of relativity in simple terms.",
            "What happens if you swallow gum?",
            "Is it true that we only use 10% of our brain?"
        ]
        
        print("\n=== TruthX Demo Responses ===\n")
        
        for question in sample_questions:
            response = generate_response(
                model,
                tokenizer,
                question,
                temperature=args.temperature
            )
            print(f"Q: {question}")
            print(f"A: {response}\n")


if __name__ == "__main__":
    main()
