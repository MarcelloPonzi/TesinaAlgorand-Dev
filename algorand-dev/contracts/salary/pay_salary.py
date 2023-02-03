from pyteal import *
from pyteal_helpers import program
UINT64_MAX = 0xFFFFFFFFFFFFFFFF


def approval():
    # Operazioni smart contract
    op_request_pay = Bytes("payme")
    op_send_pay = Bytes("pay")
    op_decline = Bytes("decline")
    op_inc_hours = Bytes("hour")

    # Smart contract Global Schema
    # Indirizzo del creatore del contratto
    global_creator = Bytes("global_creator")  # byteslice
    # Indirizzo del datore di lavoro
    global_employer = Bytes("global_employer")  # byteslice
    # Indirizzo dell'impiegato
    global_employee = Bytes("employee")  # byteslice
    # Quantità da pagare
    global_amount = Bytes("amount")  # unint64
    # Quantità da pagare per ora di lavoro
    global_amount_per_hour = Bytes("amount")  # unint64
    # Ore di lavoro
    global_hours = Bytes("hours")  # unint64
    # Pagamento richiesto
    global_requested_pay = Bytes("Requested")  # byteslice

    scratch_counter = ScratchVar(TealType.uint64)
    scratch_amount = ScratchVar(TealType.uint64)

    def setup():
        return Seq([
            App.globalPut(global_creator, Txn.sender()),
            App.globalPut(global_employer, Bytes("DNMDFULHZA2QP36U3PCFUEM4Y77LAZA6URGRBUOD3GUDSKCBIFSJAXC24U")),
            App.globalPut(global_employee, Bytes("2BX6AOEWH54BOIVUKYSZU52UXRSFKMVNGSDMUXDDRNYOC7QE4Q6TN657QI")),
            App.globalPut(global_amount, Int(0)),
            App.globalPut(global_hours, Int(10)),
            App.globalPut(global_amount_per_hour, Int(100)),
            App.globalPut(global_requested_pay, Bytes("False")),
            Approve()
        ])

    def reset():
        return Seq([
            App.globalPut(global_employer, Bytes("")),
            App.globalPut(global_employee, Bytes("")),
            App.globalPut(global_hours, Int(0)),
            App.globalPut(global_amount_per_hour, Int(0)),
        ])

    @Subroutine(TealType.none)
    def request_payment():
        return Seq([
            Assert(
                And(
                    # Verifica il mandante della transazione sia l'impiegato
                    Txn.sender() == App.globalGet(global_employee),
                    # Verifica siano state svolte almeno 8 ore di lavoro
                    # NOT WORKING
                    # Int(8) <= App.globalGet(global_hours)
                )
            ),
            #NOT WORKING
            #App.globalPut(global_requested_pay, Bytes("True")),
            scratch_amount.store((App.globalGet(global_hours) * App.globalGet(global_amount_per_hour))),
            App.globalPut(global_amount, scratch_amount.load()),
            Approve()
        ])

    @Subroutine(TealType.none)
    def decline():
        return Seq([])

    @Subroutine(TealType.none)
    def send_pay():
        return Seq([
            Assert(
                And(
                    # Verifica il pagamento sia stato richiesto
                    # NOT WORKING
                    #App.globalGet(global_requested_pay) == Bytes(
                    #    "True"),
                    # Verifica la transazione sia fatta dal datore
                    Txn.sender() == App.globalGet(global_employer),
                )
            ),

            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                # Viene sottratto il costo minimo per eseguire una transazione
                TxnField.amount: App.globalGet(global_amount) - Global.min_balance(),
                # Il datore fa da garante per la transazione
                TxnField.sender: Global.current_application_address(),
                TxnField.receiver: App.globalGet(global_employee),
                # Indirizzo al quale inviare i fondi rimanenti sul conto del garante
                TxnField.close_remainder_to: App.globalGet(global_employee),
                TxnField.fee: Int(0),  # Già pagate
            }),
            InnerTxnBuilder.Submit(),

            # Risettiamo le variabili
            App.globalPut(global_amount, Int(0)),
            App.globalPut(global_requested_pay, Bytes("False")),
            App.globalPut(global_hours, Int(0)),
            Approve()
        ])

    @Subroutine(TealType.none)
    def inc_hours():
        return Seq([
            scratch_counter.store(App.globalGet(global_hours)),
            # check overflow
            If(
                scratch_counter.load() < Int(UINT64_MAX),
                App.globalPut(global_hours, scratch_counter.load() + Int(1)),
            ),
            Approve(),
        ])

    # Programmazione degli eventi e input per le operazioni
    return program.event(
        init=Seq(
            reset(),
            setup(),
            Approve(),
        ),
        no_op=Seq(
            Cond(
                [
                    Txn.application_args[0] == op_request_pay,
                    request_payment(),
                ],
                [
                    Txn.application_args[0] == op_decline,
                    decline(),
                ],
                [
                    Txn.application_args[0] == op_send_pay,
                    send_pay(),
                ],
                [
                    Txn.application_args[0] == op_inc_hours,
                    inc_hours(),
                ],
            ),
            Reject(),
        ),
    )


def clear():
    return Approve()
