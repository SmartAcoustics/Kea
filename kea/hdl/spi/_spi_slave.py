from myhdl import block, Signal, intbv, enum, always

@block
def spi_slave(clock, parallel_out, data_valid, spi_sclk, spi_mosi, spi_ncs):
    '''
    An spi slave that will read in as many bits as are determined by the
    length of the parallel out signal, with each bit set on a rising clock
    edge. `parallel_out` should be at least 2 bits wide.

    It is assumed that the spi signals are sensibly within the clock domain
    of `clock`. This probably means passing through a CDC (e.g. a double
    buffer, clocked out by clock), which should be fairly transparent assuming
    that the frequency is `clock` is substantially higher than `spi_sclk`.
    It is assumed that spi clock period is at least four times the period
    of `clock`.

    The data will be read in most-significant bit first.

    Once all the data has been read in, `data_valid` will be set high for one
    clock cycle at which point the data can be read from `parallel_out` on the
    next rising edge of `clock`.

    The following timing diagram can be viewed in wavedrom
    (https://wavedrom.com/editor.html):

    ```wavedrom
    { "signal": [
      { "name": "spi_sclk",
      "wave": "xhlhlhlhlh|lhlhlhlhx|." },
      { "name": "spi_ncs",
      "wave": "hl........|........h.." },
      { "name": "spi_mosi",
      "wave": "x.=.=.=.=.|=.=.=.=.x|.",
      "data":["DN", "DN-1", "DN-2", "",  "D3", "D2", "D1", "D0"] },
      {"name": "clock",
      "wave": "p.........|..........."},
      { "name": "data_valid",
      "wave": "l.........|.......hl.."},
      { "name": "parallel_out",
      "wave": "x.........|.......=...",
      "data": 'D[N,N-1,N-2,..,3,2,1,0]' }
    ]}
    ```

    It is possible to have multiple sequential words read without `spi_ncs`
    going high:

    ```wavedrom
    { "signal": [
      { "name": "spi_sclk",
      "wave": "lhlhlhlhlh|lhlhlhx|.." },
      { "name": "spi_ncs",
      "wave": "l.........|......h..." },
      { "name": "spi_mosi",
      "wave": "=.=.=.=.=.|=.=.=.x...",
      "data":["A1", "A0", "BN-1", "BN-2",  "", "B2", "B1", "B0"] },
      {"name": "clock",
      "wave": "p.........|.........."},
      { "name": "data_valid",
      "wave": "l..hl.....|.....hl..."},
      { "name": "parallel_out",
      "wave": "x..=......|.....=....",
      "data": ["A[N,N-1,N-2,..,3,2,1,0]", "B[N,N-1,N-2,..,3,2,1,0]"] }
    ]}
    ```

    `spi_ncs` must be low for the whole transaction. If it goes high before
    a complete word has been read, that word will be ignored and a new word
    will be started when it goes low again.
    '''

    bitwidth = len(parallel_out)
    assert bitwidth >= 2 # necessary for the logic - should always be true

    bit_count = Signal(intbv(0, min=0, max=bitwidth))
    parallel_store = Signal(intbv(0)[len(parallel_out):])

    spi_sclk_last = Signal(False)

    @always(clock.posedge)
    def spi_reader():
        spi_sclk_last.next = spi_sclk
        data_valid.next = False

        if not spi_ncs:
            # rising edge detector
            if spi_sclk and not spi_sclk_last:
                if bit_count == bitwidth - 1:
                    bit_count.next = 0
                    parallel_out.next[0] = spi_mosi
                    parallel_out.next[bitwidth:1] = (
                        parallel_store[bitwidth-1:0])
                    data_valid.next = True
                else:
                    parallel_store.next[0] = spi_mosi
                    parallel_store.next[bitwidth:1] = (
                        parallel_store[bitwidth-1:0])
                    bit_count.next = bit_count + 1
        else:
            bit_count.next = 0

    return spi_reader

