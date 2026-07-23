# IcePi Zero JTAGG: Pipeline-Vergleich

Aktualisierte Messung vom 2026-07-23 für `::bonfire-core-soc:0`, Target
`icepizero_jtagg`, mit `fw_monitor`, ECP5-25K/CABGA256 und der
projektlokalen OSS-CAD-Toolchain (Yosys 0.67). Das Target hat einen
100-MHz-LPF-Constraint; daher sind alle drei Builds erwartungsgemäß als
Timing-Fail markiert, obwohl nextpnr die unten stehende maximale Frequenz
ermittelt.

## Ergebnisse

| Konfiguration | Sysclk-Fmax | LUT4 | TRELLIS_FF | `hazards.S` bis Monitor-Pass |
|---|---:|---:|---:|---:|
| 3 Stufen | 69,81 MHz | 3.088 | 1.617 | 230 Takte |
| 4 Stufen, historisches Shared-Result, Bypass an | 75,94 MHz | 3.037 | 1.651 | 230 Takte |
| 4 Stufen, historisches Shared-Result, Bypass aus | **83,56 MHz** | 2.868 | 1.651 | 253 Takte |
| 4 Stufen, Quellenregister, Bypass an | **84,49 MHz** | 2.927 | 1.751 | 230 Takte |
| 4 Stufen, Quellenregister, Bypass aus | 82,90 MHz | **2.657** | 1.751 | 253 Takte |

Gegenüber drei Stufen bedeutet das:

- Historisches Shared-Result mit Bypass: +6,13 MHz (+8,8 %), 51 LUT4 weniger und 34 FF
  mehr; keine zusätzliche Laufzeit im gezielten Hazard-Test.
- Historisches Shared-Result ohne Bypass: +13,75 MHz (+19,7 %), 220 LUT4 weniger und 34 FF
  mehr; der Hazard-Test benötigt wegen der RAW-Interlocks 23 zusätzliche
  Takte (+10,0 %).
- Quellenregister verschieben den Result-Mux hinter getrennte ALU-, LSU-,
  CSR- und Jump-Link-Register. Die Quellenauswahl ist als vier registrierte,
  gegenseitig exklusive One-Hot-Signale ausgeführt. Gegenüber dem bisherigen
  Vier-Stufen-Backend kostet das 100 FF. Alle vier Datenregister werden in
  jedem Takt direkt von ihrer Funktionseinheit geladen; nur der nachgelagerte
  Mux wird durch die registrierten One-Hot-Signale ausgewählt. Mit Bypass
  steigt Fmax in diesem Einzelaufbau um 8,55 MHz; ohne Bypass liegt sie
  0,66 MHz niedriger. Beide Varianten behalten die bisherige Hazard-Latenz
  bei.

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
| 4 Stufen, Quellenregister, Bypass an | `@2295` | 230 |
| 4 Stufen, Quellenregister, Bypass aus | `@2525` | 253 |

Die Taktzahl ist `(Zeitstempel + 5) / 10`, weil die erste steigende Flanke
bei Zeit 5 liegt.

## Reproduktionsbedingungen und Einschränkung

Jede Konfiguration wurde in einem eigenen frischen Build-Root erzeugt und
verwendete dieselbe `monitor.hex`-Firmware, dasselbe JTAGG-Target und
dieselbe Toolchain. Für den Vergleich wurden nur die Generatorparameter
`pipeline_length` und `writeback_bypass` geändert. Die Quellenregister-Läufe
bilden die aktuelle Vier-Stufen-Implementierung ab; die Shared-Result-Zeilen
sind historische Vergleichsmessungen. Die Builds liefen in temporären, von
der lokalen Target-Datei getrennten Build-Roots.

Das derzeitige Target setzt keinen festen nextpnr-Seed. Daher sind die Werte
Einzelmessungen und kleine Abstände können Placement-Schwankungen enthalten.
Der große Abstand beider aktuellen Vier-Stufen-Varianten zur Drei-Stufen-
Referenz ist dennoch eindeutig. Innerhalb der Source-Register-Variante liegt
der Bypass in diesem Lauf 1,59 MHz höher, benötigt aber 270 zusätzliche LUT4;
die Interlock-Variante benötigt bei engen RAW-Folgen 23 zusätzliche Takte.
