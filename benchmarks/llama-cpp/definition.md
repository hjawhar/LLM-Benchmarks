# definition

**Backend:** llama-cpp  
**Model:** models/Llama-3.2-3B-Instruct-Q4_K_M.gguf  
**Max Tokens:** 2048

## Run 1

| Metric | Value |
| ------ | ----: |
| TPS | 80.6 tok/s |
| TTFT | 781.7 ms |
| Total | 0.78 s |
| Memory | 6258 MB |

### Prompt

```
Define 'photosynthesis' in exactly two sentences.
```

### Output

```
 
Photosynthesis is the process by which plants, algae, and some bacteria convert light energy from the sun into chemical energy in the form of glucose, a type of sugar. This process is essential for life on Earth, as it provides the energy and organic compounds needed to support the food chain and sustain countless organisms.
```

## Run 2

| Metric | Value |
| ------ | ----: |
| TPS | 89.0 tok/s |
| TTFT | 651.7 ms |
| Total | 0.65 s |
| Memory | 6259 MB |

### Prompt

```
Define 'photosynthesis' in exactly two sentences.
```

### Output

```
 Photosynthesis is the process by which plants, algae, and some bacteria convert light energy from the sun into chemical energy in the form of glucose, releasing oxygen as a byproduct. This energy is used by the organisms to power their metabolic processes, while the oxygen is released into the atmosphere.
```

## Run 3

| Metric | Value |
| ------ | ----: |
| TPS | 89.3 tok/s |
| TTFT | 604.8 ms |
| Total | 0.60 s |
| Memory | 6261 MB |

### Prompt

```
Define 'photosynthesis' in exactly two sentences.
```

### Output

```
 Photosynthesis is the process by which plants, algae, and some bacteria convert light energy from the sun into chemical energy in the form of glucose. This process also produces oxygen as a byproduct, which is released into the atmosphere, supporting the life of most living organisms.
```
