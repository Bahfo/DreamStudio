class Chess:

    ### chess pieces names ###
    piece_names = {
        0: " . ",
        1: " WP",  2: " WN",  3: " WB",  4: " WR",  5: " WQ",  6: " WK",
        -1: " BP", -2: " BN", -3: " BB", -4: " BR", -5: " BQ", -6: " BK"
    }
    
    ### king valid moves and castling ###
    black_king_moved = 0
    white_king_moved = 0
    
    king_valid_moves = [
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),          ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1),
        #castle state
        (2,0),(-3,0)
    ]
    
    ### standard _chessTable representation ###
    ### negative for black and positive for white ###
    _chessTable = [
        [-4, -2, -3, -5, -6, -3, -2, -4], ### Row 0 (Rank 8) ###
        [-1, -1, -1, -1, -1, -1, -1, -1], ### Row 1 (Rank 7) ###
        [ 0,  0,  0,  0,  0,  0,  0,  0], 
        [ 0,  0,  0,  0,  0,  0,  0,  0], 
        [ 0,  0,  0,  0,  0,  0,  0,  0], 
        [ 0,  0,  0,  0,  0,  0,  0,  0], 
        [ 1,  1,  1,  1,  1,  1,  1,  1], ### Row 6 (Rank 2) ###
        [ 4,  2,  3,  5,  6,  3,  2,  4]  ### Row 7 (Rank 1) ###
    ]
                    
    def __init__(self):
        self._Black_king = (0, 4)   ### E8 ###
        self._White_king = (7, 4)   ### E1 ###

    ### PRIVATE METHOD: helper to map notation to coordinates ###
    def _to_coords(self, notation):
        notation = notation.upper()
        col_char = notation[0] 
        rank_char = notation[1] 

        ### map letter to column index  ###
        col = ord(col_char) - ord('A')
        
        ### map rank number to row index ###
        row = 8 - int(rank_char)
        
        return (row, col)

    def moveKing(self, before_str, after_str):
        """input{before_str==> the move before in chess notations
                after_str ==> same as above}
        output{modified list (to see the modefied list use the method
        print_board() )}"""
            
        ### calling the PRIVATE method internally ###
        
        r1, c1 = self._to_coords(before_str)
        r2, c2 = self._to_coords(after_str)
        
        before_pos = (r1, c1)
        after_pos = (r2, c2)

        ### check board boundaries ###
        if not (0 <= r1 < 8 and 0 <= c1 < 8 and 0 <= r2 < 8 and 0 <= c2 < 8):
            print(f"Error: Positions {before_str} or {after_str} are outside the board!")
            return

        ### calculate difference ###
        diff = (r2 - r1, c2 - c1)
        
        if diff in Chess.king_valid_moves:            
            piece_value = Chess._chessTable[r1][c1]
            target_value = Chess._chessTable[r2][c2] 
            
            ### check if piece is a king ###
            if abs(piece_value) != 6:
                print(f"Error: Piece at {before_str} is not a King!")
                return

            ### check if the traget move is white piece for white king ###
            if piece_value == 6 and target_value > 0:
                print(f"Invalid Move: White King cannot eat white piece at {after_str}!")
                return 

            ### check if the traget move is also black piece for black king ###
            if piece_value == -6 and target_value < 0:
                print(f"Invalid Move: Black King cannot eat black piece at {after_str}!")
                return 

            ### execute move on board ###
            Chess._chessTable[r2][c2] = piece_value
            Chess._chessTable[r1][c1] = 0
            if piece_value == -6 and target_value == 0:
                Chess.black_king_moved = 1            
            elif piece_value == 6 and target_value == 0:
                Chess.white_king_moved = 1
            elif piece_value == 6 and target_value == 4 and not Chess.black_king_moved:
                
                ### update private king position internally ###
                if piece_value == 6:
                    self._White_king = (r2, c2)
                    print(f"White King moved from {before_str} to {after_str}")
                elif piece_value == -6:
                    self._Black_king = (r2, c2)
                    print(f"Black King moved from {before_str} to {after_str}")
                
        else:
            print(f"Invalid move! King cannot move from {before_str} to {after_str}")

    def print_board(self):
        """input(nine)
            output(ChessTable)
            to see what is happining """
        print("\n     A     B     C     D     E     F     G     H")
        print("   " + "-" * 48)
        
        for row_index, row in enumerate(self._chessTable):
            rank_num = 8 - row_index
            row_display = f"{rank_num} | "
            
            for num in row:
                word = Chess.piece_names.get(num, " ??")
                row_display += word + " | "
            
            print(row_display + f" {rank_num}") 
            print("   " + "-" * 48)
            
        print("     A     B     C     D     E     F     G     H\n")

app = Chess()
app.print_board()