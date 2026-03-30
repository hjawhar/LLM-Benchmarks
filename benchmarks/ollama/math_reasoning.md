# math_reasoning

**Backend:** ollama  
**Model:** llama3.2:3b  
**Max Tokens:** 2048

## Run 1

| Metric | Value |
| ------ | ----: |
| TPS | 170.7 tok/s |
| TTFT | 11.1 ms |
| Total | 0.80 s |
| Memory | 2117 MB |

### Prompt

```
What is 15% of 240? Show your work step by step.
```

### Output

```
To find 15% of 240, I'll follow these steps:

1. Convert the percentage to a decimal:
15% = 0.15 (since 15 divided by 100 is 0.15)

2. Multiply the decimal by the number:
0.15 × 240 = ?

3. Perform the multiplication:
0.15 × 200 = 30
0.15 × 40 = 6

4. Add the partial results together:
30 + 6 = 36

So, 15% of 240 is 36.
```

## Run 2

| Metric | Value |
| ------ | ----: |
| TPS | 170.4 tok/s |
| TTFT | 64.5 ms |
| Total | 0.96 s |
| Memory | 2117 MB |

### Prompt

```
What is 15% of 240? Show your work step by step.
```

### Output

```
To find 15% of 240, we'll follow these steps:

1. Convert the percentage to a decimal:
15% = 0.15 (since 15/100 = 0.15)

2. Multiply the decimal by the number:
0.15 × 240 = ?

3. Perform the multiplication:
0.15 × 200 = 30
0.15 × 40 = 6
0.15 × 0 = 0

4. Add up the partial products:
30 + 6 + 0 = 36

So, 15% of 240 is equal to 36.
```

## Run 3

| Metric | Value |
| ------ | ----: |
| TPS | 170.4 tok/s |
| TTFT | 64.5 ms |
| Total | 0.97 s |
| Memory | 2117 MB |

### Prompt

```
What is 15% of 240? Show your work step by step.
```

### Output

```
To find 15% of 240, I'll follow these steps:

1. Convert the percentage to a decimal:
15% = 0.15 (since 15/100 = 0.15)

2. Multiply the decimal by the number:
0.15 x 240 = ?

3. Multiply 0.15 by 200:
0.15 x 200 = 30

4. Multiply 0.15 by 40:
0.15 x 40 = 6

5. Add the results together:
30 + 6 = 36

Therefore, 15% of 240 is 36.
```
