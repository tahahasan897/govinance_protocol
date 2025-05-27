import { Address, BigInt } from "@graphprotocol/graph-ts"
import { Transfer } from "../generated/TranscriptToken/TranscriptToken"
import { Holder, Token, DailyStat } from "../generated/schema"

let ZERO_ADDRESS = Address.fromString("0x0000000000000000000000000000000000000000")

export function handleTransfer(event: Transfer): void {
  let token = Token.load("TCRIPT")
  if (token == null) {
    token = new Token("TCRIPT")
    token.holderCount = 0
  }

  // FROM holder
  if (event.params.from != ZERO_ADDRESS) {
    let holder = Holder.load(event.params.from.toHex())
    if (holder == null) {
      holder = new Holder(event.params.from.toHex())
      holder.balance = BigInt.zero()
    }
    let before = holder.balance
    holder.balance = holder.balance.minus(event.params.value)
    holder.save()
    if (before.gt(BigInt.zero()) && holder.balance.equals(BigInt.zero())) {
      token.holderCount = token.holderCount - 1
    }
  }

  // TO holder
  if (event.params.to != ZERO_ADDRESS) {
    let holder = Holder.load(event.params.to.toHex())
    if (holder == null) {
      holder = new Holder(event.params.to.toHex())
      holder.balance = BigInt.zero()
    }
    let before = holder.balance
    holder.balance = holder.balance.plus(event.params.value)
    holder.save()
    if (before.equals(BigInt.zero()) && holder.balance.gt(BigInt.zero())) {
      token.holderCount = token.holderCount + 1
    }
  }

  token.save()

  // Daily stats
  let day = event.block.timestamp.toI32() / 86400
  let id = day.toString()
  let stat = DailyStat.load(id)
  if (stat == null) {
    stat = new DailyStat(id)
    stat.date = day * 86400
    stat.volume = BigInt.zero()
    stat.holderCount = token.holderCount
  }
  stat.volume = stat.volume.plus(event.params.value)
  stat.holderCount = token.holderCount
  stat.save()
}
