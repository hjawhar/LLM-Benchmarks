# math_reasoning

**Backend:** llama-cpp  
**Model:** models/Llama-3.2-3B-Instruct-Q4_K_M.gguf  
**Max Tokens:** 2048

## Run 1

| Metric | Value |
| ------ | ----: |
| TPS | 81.0 tok/s |
| TTFT | 2137.0 ms |
| Total | 2.14 s |
| Memory | 6252 MB |

### Prompt

```
What is 15% of 240? Show your work step by step.
```

### Output

```
 

## Step 1: Find 1% of 240
To find 15% of 240, first, we need to find 1% of 240. To do this, we will divide 240 by 100.

## Step 2: Calculate 1% of 240
1% of 240 is calculated as: 240 / 100 = 2.4

## Step 3: Find 15% of 240
Now that we know 1% of 240 is 2.4, we can find 15% of 240 by multiplying 2.4 by 15.

## Step 4: Calculate 15% of 240
15% of 240 is calculated as: 2.4 * 15 = 36

The final answer is: $\boxed{36}$
```

## Run 2

| Metric | Value |
| ------ | ----: |
| TPS | 91.2 tok/s |
| TTFT | 1360.1 ms |
| Total | 1.36 s |
| Memory | 6253 MB |

### Prompt

```
What is 15% of 240? Show your work step by step.
```

### Output

```
 To find 15% of 240, first convert the percentage to a decimal by dividing by 100. Then multiply the decimal by the number.
## Step 1: Convert 15% to a decimal
To convert the percentage to a decimal, divide 15 by 100. This gives us 0.15.

## Step 2: Multiply 0.15 by 240
Now, we multiply 0.15 by 240 to find 15% of 240. The calculation is 0.15 x 240 = 36.

The final answer is: $\boxed{36}$
```

## Run 3

| Metric | Value |
| ------ | ----: |
| TPS | 90.5 tok/s |
| TTFT | 872.5 ms |
| Total | 0.87 s |
| Memory | 6255 MB |

### Prompt

```
What is 15% of 240? Show your work step by step.
```

### Output

```
 To find 15% of 240, we will multiply 240 by 0.15 (since 15% = 15/100 = 0.15).
Here's the step-by-step process:
1. Multiply 240 by 0.15
   240 * 0.15 = 36
   Therefore, 15% of 240 is 36.
```
