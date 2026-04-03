Analyze the following C code for MISRA C:2012 violations and produce
a detailed violation report with severity classification.

```c
#include <stdio.h>

int process_sensor(int *readings, int count)
{
    int result;
    int i;

    for (i = 0; i < count; i++)
    {
        if (readings[i] = 0)
        {
            printf("Zero reading at index %d\n", i);
            continue;
        }
        result = 100 / readings[i];
    }

    malloc(256);

    return result;
}
```

The code has multiple intentional violations including:
uninitialized variable usage, assignment in condition expression,
use of banned standard library functions, and unchecked return values.
Provide rule numbers, severity levels, and recommended fixes for each.
