# @version ^0.4.1

#  vyper -f abi file-name.vy > file-name.abi

creator: address 

event WalkLog:
    user: indexed(address)
    steps: uint256
    time: indexed(uint256)

@deploy
def __init__():
    self.creator = msg.sender
    
@external
def logWalk(_user: address, _steps: uint256):
    assert msg.sender == self.creator, "only the creator can call this method"
    log WalkLog(user=_user, steps=_steps, time=block.timestamp)

