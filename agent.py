import sys
import json
import os
import re
import subprocess
from datetime import datetime
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

class CLIAgent:
    def __init__(self, model_path="./phi2fineTuned/models/phi2-lora-cli-final"):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.logs_dir = "logs"
        self.trace_file = os.path.join(self.logs_dir, "trace.jsonl")
        
        
        os.makedirs(self.logs_dir, exist_ok=True)
        
        self.load_model()
    
    def load_model(self):
        print("Loading fine-tuned Phi-2 model...")
        
        try:
            
            if not os.path.exists(self.model_path):
                print(f"Fine-tuned model not found at {self.model_path}")
                print("Falling back to base Phi-2 model...")
                self.load_base_model()
                return
            
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, 
                trust_remote_code=True
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            
            base_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/phi-2",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
            )
            
            
            self.model = PeftModel.from_pretrained(base_model, self.model_path)
            
            print(f"Fine-tuned model loaded successfully!")
            print(f"Device: {next(self.model.parameters()).device}")
            
        except Exception as e:
            print(f"Error loading fine-tuned model: {e}")
            print("Falling back to base model...")
            self.load_base_model()
    
    def load_base_model(self):
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                "microsoft/phi-2", 
                trust_remote_code=True
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            self.model = AutoModelForCausalLM.from_pretrained(
                "microsoft/phi-2",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
            )
            
            print("Base Phi-2 model loaded as fallback")
            
        except Exception as e:
            print(f"Failed to load base model: {e}")
            sys.exit(1)
    
    def format_prompt(self, instruction):
        return f"### Instruction:\n{instruction}\n\n### Response:\n"
    
    def generate_plan(self, instruction, max_new_tokens=200):
        formatted_prompt = self.format_prompt(instruction)
        
        inputs = self.tokenizer(formatted_prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        
        input_length = inputs['input_ids'].shape[1]
        response_tokens = outputs[0][input_length:]
        response = self.tokenizer.decode(response_tokens, skip_special_tokens=True)
        
        
        response = response.strip()
        
        
        lines = response.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and line not in cleaned_lines:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def extract_first_command(self, plan):
        lines = plan.split('\n')
        
        
        command_patterns = [
            r'^([a-zA-Z][\w\-]*(?:\s+[\w\-\.\/\*\=\&\|]+)*)\s*$',  
            r'^\$?\s*([a-zA-Z][\w\-]*(?:\s+[\w\-\.\/\*\=\&\|]+)*)\s*$',  
            r'`([^`]+)`',  
            r'^(?:Run|Execute|Use):\s*(.+)$',  
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            
            if any(word in line.lower() for word in ['step', 'first', 'then', 'next', 'explanation', 'note']):
                continue
            
            for pattern in command_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    command = match.group(1).strip()
                    
                    if self.is_shell_command(command):
                        return command
        
        
        if lines:
            first_line = lines[0].strip()
            if self.is_shell_command(first_line):
                return first_line
        
        return None
    
    def is_shell_command(self, text):
        if not text:
            return False
        
        text = re.sub(r'^(\$\s*|sudo\s+)', '', text.strip())
        
        
        shell_commands = [
            'git', 'tar', 'find', 'python', 'pip', 'head', 'tail', 'top', 'ps',
            'ls', 'cd', 'cp', 'mv', 'rm', 'mkdir', 'rmdir', 'chmod', 'chown',
            'grep', 'sed', 'awk', 'sort', 'uniq', 'wc', 'cat', 'echo', 'touch',
            'which', 'whereis', 'locate', 'du', 'df', 'free', 'uptime', 'whoami',
            'id', 'groups', 'su', 'sudo', 'ssh', 'scp', 'rsync', 'curl', 'wget',
            'vim', 'nano', 'emacs', 'less', 'more', 'source', 'export', 'alias',
            'history', 'jobs', 'bg', 'fg', 'nohup', 'screen', 'tmux', 'crontab',
            'systemctl', 'service', 'mount', 'umount', 'fdisk', 'lsblk', 'lscpu',
            'lsmem', 'lsusb', 'lspci', 'ifconfig', 'ip', 'netstat', 'ss', 'ping',
            'traceroute', 'nslookup', 'dig', 'iptables', 'ufw', 'firewall-cmd'
        ]
        
        
        first_word = text.split()[0] if text.split() else ''
        return first_word.lower() in shell_commands
    
    def execute_dry_run(self, command):
        print(f"\nExecuting (dry-run): {command}")
        
        
        try:
            echo_command = f"echo '{command}'"
            result = subprocess.run(
                echo_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"Command echoed successfully: {result.stdout.strip()}")
                return True, result.stdout.strip()
            else:
                print(f"Echo failed: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            print("Command timed out")
            return False, "Command timed out"
        except Exception as e:
            print(f"Error executing command: {e}")
            return False, str(e)
    
    def log_trace(self, instruction, plan, command, execution_result, success):
        trace_entry = {
            "timestamp": datetime.now().isoformat(),
            "instruction": instruction,
            "generated_plan": plan,
            "extracted_command": command,
            "execution_success": success,
            "execution_result": execution_result,
            "model_path": self.model_path
        }
        
        
        with open(self.trace_file, 'a') as f:
            f.write(json.dumps(trace_entry) + '\n')
    
    def process_instruction(self, instruction):
        print(f"\nInstruction: {instruction}")
        print("=" * 60)
        
        
        print("Generating step-by-step plan...")
        plan = self.generate_plan(instruction)
        
        print(f"\nGenerated Plan:")
        print("-" * 40)
        print(plan)
        print("-" * 40)
        
        
        command = self.extract_first_command(plan)
        
        execution_result = None
        success = False
        
        # if command:
        #     print(f"\nExtracted Command: {command}")
            
            
        #     success, execution_result = self.execute_dry_run(command)
            
        # else:
        #     print("\nNo executable command found in the plan")
        #     execution_result = "No command extracted"
        
        
        self.log_trace(instruction, plan, command, execution_result, success)
        
        print(f"\nLogged to: {self.trace_file}")
        
        return {
            "instruction": instruction,
            "plan": plan,
            "command": command,
            "success": success,
            "execution_result": execution_result
        }

def main():
    if len(sys.argv) != 2:
        print("Usage: python agent.py \"Your command instruction here\"")
        print("\nExamples:")
        print("  python agent.py \"Create a new Git branch and switch to it\"")
        print("  python agent.py \"Compress the folder reports into reports.tar.gz\"")
        print("  python agent.py \"List all Python files in the current directory recursively\"")
        sys.exit(1)
    
    instruction = sys.argv[1]
    
    print("CLI Agent for Fine-tuned Phi-2")
    print("=" * 60)
    
    
    try:
        agent = CLIAgent()
    except Exception as e:
        print(f"Failed to initialize agent: {e}")
        sys.exit(1)
    
    
    try:
        result = agent.process_instruction(instruction)
        
        print("\nProcessing completed!")
        print(f"Command extracted: {'Yes' if result['command'] else 'No'}")
        print(f"Execution successful: {'Yes' if result['success'] else 'No'}")
        
    except Exception as e:
        print(f"Error processing instruction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()