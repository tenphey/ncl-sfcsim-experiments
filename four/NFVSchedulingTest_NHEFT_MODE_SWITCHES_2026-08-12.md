# NFVSchedulingTest: Algorithm Switches and NHEFT Two-Mode Usage

Date: 2026-08-12

## 1. Why this change was added

The recent change in `NFVSchedulingTest.java` was introduced to avoid wasting
experiment time.

Previously, if we wanted to compare:

- baseline `NHEFT`
- gated `NHEFT` (for example `GHEFT`)

we usually had to launch Java twice.

That caused a problem:

- `HEFT`, `DHEFT`, and baseline `NHEFT` were also recomputed twice
- for the same seed, those baseline results were duplicated
- this consumed experiment time unnecessarily

So now the Java entry supports:

- selecting which algorithms should run
- running two different `NHEFT` modes in one Java execution

In other words, one launch can now produce:

- shared baseline algorithms once
- baseline `NHEFT` once
- comparison `NHEFT` mode once

## 2. What was changed

The main changes are in:

- `src/net/gripps/cloud/nfv/main/NFVSchedulingTest.java`

The entry now has two new ideas:

### 2.1 Algorithm run switches

The following properties decide which algorithms are actually executed:

- `run_heft`
- `run_dheft`
- `run_nheft`
- `run_nheft_mode2`

They are all read from the same `.properties` file passed to
`NFVSchedulingTest`.

Default behavior:

- `run_heft`: default `1`
- `run_dheft`: default `1`
- `run_nheft`: default `1`
- `run_nheft_mode2`: default depends on whether `mode2` is enabled

### 2.2 Two NHEFT modes

Now `NFVSchedulingTest` can run two NHEFT-style modes in one launch:

- `NHEFT mode1`
  - this is the ordinary baseline `NHEFT`
  - it uses the normal properties such as:
    - `nheft_vcpu_eft_tolerance`
    - `nheft_vcpu_open_requires_comp_advantage`
    - `nheft_vcpu_open_requires_drt_advantage`
    - `nheft_vcpu_open_requires_irt_advantage`
    - `nheft_vcpu_open_gate_logic`
- `NHEFT mode2`
  - this is the optional comparison mode
  - label is configurable
  - default label is `GHEFT`
  - it uses a separate prefix:
    - `nheft_mode2_enabled`
    - `nheft_mode2_label`
    - `nheft_mode2_vcpu_eft_tolerance`
    - `nheft_mode2_open_requires_comp_advantage`
    - `nheft_mode2_open_requires_drt_advantage`
    - `nheft_mode2_open_requires_irt_advantage`
    - `nheft_mode2_open_gate_logic`

So the important point is:

- `mode1` and `mode2` are both still `NHEFT_VNFAlgorithm`
- what changes is the runtime parameter set applied before each run

## 3. Internal execution logic

The helper method:

- `runNHEFTMode(...)`

does the following:

1. apply one mode configuration to `NFVUtil`
2. deep-copy the base `SFC`
3. deep-copy the base `NFVEnvironment`
4. run `NHEFT_VNFAlgorithm`
5. print results using that mode's label

This means:

- baseline `NHEFT` and `GHEFT` do not share mutable scheduling state
- they use the same seed and the same original input
- but each mode still gets its own deep-copied scheduling world

Also, after `mode2` finishes, the code restores the baseline `mode1`
parameters, so later helper logic still sees the normal `NHEFT` settings.

## 4. Meaning of the two modes

### 4.1 Mode1

`mode1` is the ordinary `NHEFT`.

Its parameters come from the normal NHEFT properties:

```properties
nheft_vcpu_eft_tolerance=0.0
nheft_vcpu_open_requires_comp_advantage=0
nheft_vcpu_open_requires_drt_advantage=0
nheft_vcpu_open_requires_irt_advantage=0
nheft_vcpu_open_gate_logic=all
```

This is the baseline.

### 4.2 Mode2

`mode2` is the optional comparison mode.

For example, if we want `GHEFT`, we can write:

```properties
nheft_mode2_enabled=1
nheft_mode2_label=GHEFT
nheft_mode2_vcpu_eft_tolerance=0.0
nheft_mode2_open_requires_comp_advantage=1
nheft_mode2_open_requires_drt_advantage=0
nheft_mode2_open_requires_irt_advantage=0
nheft_mode2_open_gate_logic=all
```

That means:

- baseline `NHEFT` still runs with its own ordinary parameters
- `GHEFT` runs as another `NHEFT`-style pass with stricter opening rules

## 5. Gate logic note

The gate logic string currently supports:

- `all`
- `and`
- `strict`
- `0`

These all mean:

- every enabled gate must be satisfied

It also supports:

- `any`
- `or`
- `relaxed`
- `1`

These all mean:

- among enabled gates, satisfying one is enough

Important:

- `EFT_new < EFT_used` is still the basic prerequisite in the algorithm logic
- the gate logic only affects how the enabled extra gates are combined

## 6. Algorithm switch properties

### 6.1 Shared switches

```properties
run_heft=1
run_dheft=1
run_nheft=1
run_nheft_mode2=0
```

Meaning:

- `run_heft=1`: run `HEFT`
- `run_dheft=1`: run `DHEFT`
- `run_nheft=1`: run baseline `NHEFT`
- `run_nheft_mode2=1`: run the optional second NHEFT-style mode

### 6.2 Special default behavior of mode2

If:

```properties
nheft_mode2_enabled=1
```

but `run_nheft_mode2` is omitted, then:

- `mode2` is run by default

This was kept to preserve the old comparison-style behavior.

If:

```properties
run_nheft_mode2=1
```

but:

```properties
nheft_mode2_enabled=0
```

then:

- Java prints a warning
- the second mode is skipped

## 7. Launch command

The Java command itself does not change.

Typical manual launch:

```bash
java -Xmn500m -Xmx1000m -Xms1000m \
  -cp ./classes:lib/commons-math-2.0.jar:lib/ncl-taskschedsim.jar \
  net.gripps.cloud.nfv.main.NFVSchedulingTest \
  nheft.properties
```

Only the `.properties` contents decide:

- which algorithms run
- whether `mode2` exists
- what label and gate rules `mode2` uses

## 8. Startup examples

### Example A: Full baseline only

Use this when we only want the ordinary reference algorithms:

- `HEFT`
- `DHEFT`
- baseline `NHEFT`

```properties
run_heft=1
run_dheft=1
run_nheft=1
run_nheft_mode2=0

nheft_mode2_enabled=0
```

Expected result:

- `HEFT` runs
- `DHEFT` runs
- baseline `NHEFT` runs
- no `GHEFT` or second mode

This is suitable for future shared-baseline scenario folders such as:

- `e01x`, `e02x`, ...

### Example B: DHEFT + NHEFT + GHEFT in one launch

Use this when we want one shared baseline plus one gated comparison mode:

```properties
run_heft=0
run_dheft=1
run_nheft=1
run_nheft_mode2=1

nheft_mode2_enabled=1
nheft_mode2_label=GHEFT
nheft_mode2_vcpu_eft_tolerance=0.0
nheft_mode2_open_requires_comp_advantage=1
nheft_mode2_open_requires_drt_advantage=0
nheft_mode2_open_requires_irt_advantage=0
nheft_mode2_open_gate_logic=all
```

Expected result:

- `DHEFT` runs once
- baseline `NHEFT` runs once
- `GHEFT` runs once
- no duplicated `DHEFT`

This is the main pattern intended for the new `four/` experiment design.

### Example C: Only GHEFT

Use this when we want to test the second mode alone:

```properties
run_heft=0
run_dheft=0
run_nheft=0
run_nheft_mode2=1

nheft_mode2_enabled=1
nheft_mode2_label=GHEFT
nheft_mode2_vcpu_eft_tolerance=0.0
nheft_mode2_open_requires_comp_advantage=1
nheft_mode2_open_requires_drt_advantage=0
nheft_mode2_open_requires_irt_advantage=0
nheft_mode2_open_gate_logic=all
```

Expected result:

- only `GHEFT` runs

### Example D: Keep HEFT too

If we still want all four outputs:

- `HEFT`
- `DHEFT`
- baseline `NHEFT`
- `GHEFT`

then use:

```properties
run_heft=1
run_dheft=1
run_nheft=1
run_nheft_mode2=1

nheft_mode2_enabled=1
nheft_mode2_label=GHEFT
```

and then add the desired `mode2` gate parameters.

## 9. Example console output

When both NHEFT modes are enabled, the console now shows both the mode config
and the run config.

Typical structure:

```text
[NHEFT-MODE1] label=NHEFT / ...
[NHEFT-MODE2] label=GHEFT / ...
[RUN-CONFIG] run_heft=0 / run_dheft=1 / run_nheft=1 / run_nheft_mode2=1 (GHEFT)
```

And later:

```text
[DHEFT]makespan:...
[NHEFT]makespan:...
[GHEFT]makespan:...
```

This is exactly what the Python scripts in `experiments/four/` can now rely on.

## 10. One important limitation

If DAG export is enabled, the current code still requires:

- `HEFT`
- `DHEFT`
- baseline `NHEFT`

to all be present.

So if DAG export is requested while one of them is disabled, export is skipped.

In short:

- experiment comparison flexibility is now higher
- DAG export still expects the classic baseline trio

## 11. Recommended usage for the new four-series design

For the future `four/` experiment map, the recommended split is:

### Shared-baseline series

Run once per scenario:

- `HEFT`
- `DHEFT`
- baseline `NHEFT`

This becomes the common baseline folder.

### Gated series

Run only the corresponding gated variant against the same scenario parameters.

This avoids recomputing identical baseline results over and over again.

That is the whole reason this entry refactor was introduced.

