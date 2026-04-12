# リスク管理

- **Status**: draft
- **Created**: 2026-04-12
- **Updated**: 2026-04-12

## 概要

リスク管理は、トレードにおける損失を制限し資金を保全するための体系的なアプローチである。ポジションサイジング、ストップロス設定、リスクリワード比の管理が中核的な要素となる。

## 詳細

### ポジションサイジング（2%ルール）

[[yamamoto-2026-macd-swing-strategy]]では、1トレードあたりのリスクを総資金の2%以内に制限する「2%ルール」を推奨。連続損失が発生しても資金の大幅減少を防止する。

### ストップロス設定

- **ATRベース**: [[yamamoto-2026-macd-swing-strategy]]ではATR（Average True Range）を用いたストップロスを推奨
- **ATR 1.5倍**: [[suzuki-2025-rsi-divergence]]ではATRの1.5倍をストップロス幅の目安としている
- **スウィングハイ/ロー基準**: 直近のスウィングハイ/ローの外側に設定する手法も提示

### リスクリワード比

[[suzuki-2025-rsi-divergence]]では、最低1:2のリスクリワード比を確保することを推奨している。

## 関連ソース

- [[yamamoto-2026-macd-swing-strategy]] — 2%ルールとATRベースのストップロス
- [[suzuki-2025-rsi-divergence]] — ATR 1.5倍のストップロスとリスクリワード1:2

## 関連概念

- [[atr]]
- [[swing-trade]]
- [[macd]]
- [[rsi]]

## 関連エンティティ

- [[yamamoto-kenichi]]
- [[suzuki-miho]]
