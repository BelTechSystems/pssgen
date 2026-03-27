// Canonical v0 test fixture: 8-bit up/down counter
module up_down_counter #(
    parameter WIDTH = 8
) (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        enable,
    input  logic        up_down,
    output logic [7:0]  count
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= '0;
        else if (enable)
            count <= up_down ? count + 1 : count - 1;
    end
endmodule
