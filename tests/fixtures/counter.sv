// IEEE 1800-2017
module up_down_counter #(
  parameter int WIDTH = 8
)(
  input  logic              clk,
  input  logic              rst_n,
  input  logic              enable,
  input  logic              up_down,
  output logic [WIDTH-1:0]  count
);
  always_ff @(posedge clk) begin : COUNT_p
    if (!rst_n)
      count <= '0;
    else if (enable)
      count <= up_down ? count + 1 : count - 1;
  end
endmodule
