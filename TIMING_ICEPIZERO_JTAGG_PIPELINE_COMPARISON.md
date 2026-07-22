# IcePi Zero JTAGG: Pipeline-Vergleich

Messung vom 2026-07-22 für `::bonfire-core-soc:0`, Target
`icepizero_jtagg`, mit `fw_monitor`, ECP5-25K/CABGA256 und der
projektlokalen OSS-CAD-Toolchain (Yosys 0.67). Das Target hat einen
100-MHz-LPF-Constraint; daher sind alle drei Builds erwartungsgemäß als
Timing-Fail markiert, obwohl nextpnr die unten stehende maximale Frequenz
ermittelt.

## Ergebnisse

| Konfiguration | Sysclk-Fmax | LUT4 | TRELLIS_FF | `hazards.S` bis Monitor-Pass |
|---|---:|---:|---:|---:|
| 3 Stufen | 69,81 MHz | 3.088 | 1.617 | 230 Takte |
| 4 Stufen, Writeback-Bypass an | 75,94 MHz | 3.037 | 1.651 | 230 Takte |
| 4 Stufen, Writeback-Bypass aus | **83,56 MHz** | **2.868** | 1.651 | 253 Takte |

Gegenüber drei Stufen bedeutet das:

- Vier Stufen mit Bypass: +6,13 MHz (+8,8 %), 51 LUT4 weniger und 34 FF
  mehr; keine zusätzliche Laufzeit im gezielten Hazard-Test.
- Vier Stufen ohne Bypass: +13,75 MHz (+19,7 %), 220 LUT4 weniger und 34 FF
  mehr; der Hazard-Test benötigt wegen der RAW-Interlocks 23 zusätzliche
  Takte (+10,0 %).

Die Fmax-Werte sind jeweils der letzte Sysclk-Wert in `next.log` nach dem
vollständigen Routing. Die Ressourcenwerte stammen aus der abschließenden
Yosys-Zellstatistik.

## Ausführungsmessung

`code/core-tests/hazards.S` enthält direkte Producer-Consumer-Folgen für
ALU, Shifter, Load, Store, Branch, CSR sowie JAL/JALR. Die MyHDL-Clock hat
eine Periodendauer von 10; Monitor-Schreibzugriffe liegen auf steigenden
Flanken. Die abschließenden Monitor-Zeitstempel waren:

| Konfiguration | Monitor-Zeitstempel | Taktzahl |
|---|---:|---:|
| 3 Stufen | `@2295` | 230 |
| 4 Stufen, Bypass an | `@2295` | 230 |
| 4 Stufen, Bypass aus | `@2525` | 253 |

Die Taktzahl ist `(Zeitstempel + 5) / 10`, weil die erste steigende Flanke
bei Zeit 5 liegt.

## Reproduktionsbedingungen und Einschränkung

Jede Konfiguration wurde in einem eigenen frischen Build-Root erzeugt und
verwendete dieselbe `monitor.hex`-Firmware, dasselbe JTAGG-Target und
dieselbe Toolchain. Für den Vergleich wurden nur die Generatorparameter
`pipeline_length` und `writeback_bypass` geändert.

Das derzeitige Target setzt keinen festen nextpnr-Seed. Daher sind die Werte
Einzelmessungen und kleine Abstände können Placement-Schwankungen enthalten.
Die großen Abstände in diesem Lauf sind dennoch eindeutig: Der zusätzliche
Forwarding-Mux kostet Timing und LUTs, während die Interlock-Variante dafür
bei engen RAW-Folgen Ausführungszeit verliert.
