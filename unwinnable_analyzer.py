# The original version of this code was created by Jed Grabman

# It is licensed under the GNU General Public License v3.0

# No Guarantee is made about its accuracy or completeness
# Refer to the license for full details

# Special thanks to:
# Chess Unwinnability Analyzer: <https://chasolver.org/>
# Python-chess: <https://python-chess.readthedocs.io/>
# Lichess: <https://lichess.org>

import chess
import os
import re
import lichess.api

PROGRAM_DIRECTORY = r'ENTER\YOUR\DIRECTORY\HERE'
RESULTS_DIRECTORY = r'results'
ABANDONED_FILE = 'unwinnable_abandon.txt'
NON_ABANDONDED_FILE = 'unwinnable_no_abandon.txt'
RESULTS_BY_PLY_DIRECTORY = os.path.join(RESULTS_DIRECTORY, r'ply')
DETAILED_RESULTS_DIRECTORY = r'results/ply_outcome/'
MAX_PLY_FILE = "max_ply.txt"
os.chdir(PROGRAM_DIRECTORY)

f = open('unwinnable_list.txt', 'r')
positions_with_id = f.readlines() #92693
f.close()

if not os.path.exists(ABANDONED_FILE):
    f_abandon = open('unwinnable_abandon.txt', 'w')
    f_timeout = open('unwinnable_no_abandon.txt', 'w')
    abandon_positions_list = []
    timeout_positions_list = []
    counter = 0
    abandon = False
    counter_limit = len(positions_with_id) # 92693
    while counter < counter_limit: 
        print("Working on games:", counter, "/", counter_limit)
        counter_upper = min(counter+300, counter_limit)
        id_array = [0] * (counter_upper - counter)
        pos_id_dict = dict()
        for i in range(counter, counter_upper):
            position = positions_with_id[i]
            position_len = len(position)
            id = position[position_len - 9:position_len - 1]
            pos_id_dict[id] = position
            id_array[i - counter] = id
        counter = counter_upper
        games = lichess.api.games_by_ids(id_array, pgnInJson=True, literate=True)
        for game in games:
            if type(game) == dict:
                position = pos_id_dict[game['id']]
                game_pgn = game['pgn']
                game_pgn_len = len(game_pgn)
                result = game_pgn[len(game_pgn) - 14:len(game_pgn) - 10]
                if result == "game": # "left the game"
                    abandon_positions_list.append(position)
                elif result == "time": # "wins on time"
                    timeout_positions_list.append(position)
                else:
                    print("unexpected game result!")
                    abandon = True
                    break
            else:
                print("Not a dictionary! Were we rate limited?")
                abandon = True
                break # be nice if we get rate limited
        if abandon:
            break
    print('writing')
    _ = f_abandon.writelines(abandon_positions_list)
    _ = f_timeout.writelines(timeout_positions_list)
    print('done')
    f_abandon.close()
    f_timeout.close()

f = open('unwinnable_no_abandon.txt', 'r')
positions_with_id = f.readlines() #84758
positions = {re.sub('\ \d.*', '', position.strip()) for position in positions_with_id} #67789
f.close()

boards = [chess.Board(position) for position in positions] #67789

def ply_to_game_end(board, color, max_ply):
    if max_ply < 0:
        return None
    if board.is_stalemate():
        return 0
    if board.has_insufficient_material(not color):
        return 0
    if board.is_checkmate() and board.turn != color: #It's not your turn, because you delivered checkmate
        return 0
    moves_list = list(board.legal_moves)
    max_ply_to_unwinnable = 0
    for move in moves_list:
        board_copy = board.copy()
        board_copy.push(move)
        ply_to_unwinnable = ply_to_game_end(board_copy, color, max_ply - 1)
        if ply_to_unwinnable is None:
            return None
        if ply_to_unwinnable > max_ply_to_unwinnable:
            max_ply_to_unwinnable = ply_to_unwinnable
    return 1 + max_ply_to_unwinnable

if not os.path.exists(RESULTS_DIRECTORY):
    os.mkdir(RESULTS_DIRECTORY)
if not os.path.exists(RESULTS_BY_PLY_DIRECTORY):
    os.mkdir(RESULTS_BY_PLY_DIRECTORY)

filelist = os.listdir(RESULTS_BY_PLY_DIRECTORY)
for file in filelist:
    os.remove(os.path.join(RESULTS_BY_PLY_DIRECTORY, file))

max_ply_to_check = 10

print("Checking max ply per board")
percent_progress = 0
for i in range(len(boards)):
    percent_finished = int(100 * i / len(boards))
    if percent_finished > percent_progress + 4:
        print(str(percent_finished) + "% done")
        percent_progress = percent_finished
    board = boards[i]
    max_ply = ply_to_game_end(board, board.turn, max_ply_to_check)
    if max_ply is None:
        max_ply = "max"
    f_name = "results/ply/" + str(max_ply) + "_ply.txt"
    f = open(f_name, 'a')
    _ = f.write(re.sub('\ \d.*', '', board.fen()) + "\n")
    f.close()


def board_to_tuple(board):
    wp = int(board.pieces(chess.PAWN, chess.WHITE))
    wn = int(board.pieces(chess.KNIGHT, chess.WHITE))
    wb = int(board.pieces(chess.BISHOP, chess.WHITE))
    wr = int(board.pieces(chess.ROOK, chess.WHITE))
    wq = int(board.pieces(chess.QUEEN, chess.WHITE))
    wk = int(board.pieces(chess.KING, chess.WHITE))

    bp = int(board.pieces(chess.PAWN, chess.BLACK))
    bn = int(board.pieces(chess.KNIGHT, chess.BLACK))
    bb = int(board.pieces(chess.BISHOP, chess.BLACK))
    br = int(board.pieces(chess.ROOK, chess.BLACK))
    bq = int(board.pieces(chess.QUEEN, chess.BLACK))
    bk = int(board.pieces(chess.KING, chess.BLACK))

    ep_square = board.ep_square #en passant square
    turn = board.turn
    piece_tuple = (wp, wn, wb, wr, wq, wk, bp, bn, bb, br, bq, bk, ep_square, turn)
    return piece_tuple

def tuple_to_board(chess_tuple):
    board = chess.Board()
    board.clear()
    for i in range(12):
        squareset = chess_tuple[i]
        if i < 6:
            color = chess.WHITE
        else:
            color = chess.BLACK
        if i % 6 == 0:
            piece = chess.PAWN
        else:
            piece = piece + 1
        chess_piece = chess.Piece(piece, color)
        square_list = list(chess.SquareSet(chess_tuple[i]))
        for square in square_list:
            board.set_piece_at(square, chess_piece)
    board.ep_square = chess_tuple[12]
    board.turn = chess_tuple[13]
    return board

# check number of positions

filelist = os.listdir(RESULTS_BY_PLY_DIRECTORY)
filelist = {file for file in filelist}
filelist.remove('max_ply.txt') # hacky
print('Creating detailed results lists from ply files')
if not os.path.exists(DETAILED_RESULTS_DIRECTORY):
    os.mkdir(DETAILED_RESULTS_DIRECTORY)
    for file in filelist:
        print(file) # e.g. '3_ply.txt'
        f_ply = open('results/ply/' + file, 'r')
        fens = f_ply.read().splitlines()
        f_ply.close()
        boards = [chess.Board(fen) for fen in fens] 
        ply = re.sub('_.*', '', file)
        for i in range(len(boards)):
            board_original = boards[i]
            board = board_original.copy()
            finished_boards = set()
            boards_to_analyze = set()
            boards_to_analyze.add(board_to_tuple(board))
            color = not board.turn

            while len(boards_to_analyze) > 0:
                board_analyzing_tuple = boards_to_analyze.pop()
                board_analyzing = tuple_to_board(board_analyzing_tuple)
                finished_boards.add(board_analyzing_tuple)
                if not board_analyzing.has_insufficient_material(color):
                    legal_moves = list(board_analyzing.legal_moves)
                    for move in legal_moves:
                        board_copy = board_analyzing.copy()
                        board_copy.push(move)
                        board_tuple = board_to_tuple(board_copy)
                        if board_tuple not in finished_boards:
                            boards_to_analyze.add(board_tuple)
                boards_to_analyze = boards_to_analyze.difference(finished_boards)
            boards_possible = [tuple_to_board(tuple) for tuple in finished_boards]
            checkmates = any([possible_board.is_checkmate() for possible_board in boards_possible])
            stalemates = any([possible_board.is_stalemate() for possible_board in boards_possible])
            ims = any([possible_board.has_insufficient_material(not board.turn) and not possible_board.is_checkmate() and not possible_board.is_stalemate() for possible_board in boards_possible])
            tag = ""
            if checkmates:  
                tag = tag + "Checkmate"
            if stalemates:
                tag = tag + "Stalemate"
            if ims:
                tag = tag + "InsufficientMaterial"
            f_name = DETAILED_RESULTS_DIRECTORY + "/" + ply + "_" + tag + ".txt"
            f = open(f_name, 'a')
            _ = f.write(board_original.fen() + "\n")
            f.close()
    print('done')

def find_unmovable_pieces(board, movable_squares = chess.SquareSet(0)):
    board_copy = board.copy()
    for square in movable_squares:
        board_copy.remove_piece_at(square)
    legal_moves = both_sides_moves(board_copy)
    while len(legal_moves) > 0:
        from_squares = [move.from_square for move in legal_moves]
        for square in from_squares:
            board_copy.remove_piece_at(square)
        legal_moves = both_sides_moves(board_copy)
    return board_copy

def both_sides_moves(board):
    board_copy = board.copy()
    legal_moves = set(board_copy.legal_moves)
    board_copy.turn = not board_copy.turn
    legal_moves = legal_moves.union(set(board_copy.legal_moves))
    white_king_square = board.king(chess.WHITE)
    black_king_square = board.king(chess.BLACK)
    #python-chess considers capturing the king legal if you may do so on your turn
    legal_moves = {move for move in legal_moves if move.to_square != white_king_square and move.to_square != black_king_square}
    return legal_moves

def get_board_occupied_binary(board):
    occupied_squares_list = board.occupied_co
    occupied_squares_bin = occupied_squares_list[chess.WHITE] + occupied_squares_list[chess.BLACK]
    return occupied_squares_bin


def find_board_difference(board, board_reduced):
    board_occupied_bin = get_board_occupied_binary(board)
    board_reduced_occupied_bin = get_board_occupied_binary(board_reduced)
    board_difference_bin = board_occupied_bin - board_reduced_occupied_bin
    square_difference = chess.SquareSet(board_difference_bin)
    return square_difference

def is_blockaded(board, known_movable = chess.SquareSet(0)):
    if board.is_check(): 
        moves = list(board.legal_moves)
        for move in moves:
            board_copy = board.copy()
            board_copy.push(move)
            if not is_blockaded(board_copy):
                return False
        return True
    unmovable_board = find_unmovable_pieces(board, known_movable)
    blank_board = chess.Board()
    blank_board.clear()
    blank_board.turn = unmovable_board.turn
    if unmovable_board == blank_board:
        return False
    movable_squares = find_board_difference(board, unmovable_board)
    capture_squares = chess.SquareSet()
    for square in movable_squares:
        piece = board.piece_at(square)
        affected_squares = get_affected_squares(unmovable_board, piece, square, board)
        if affected_squares is not None:
            if type(affected_squares) == tuple:
                capture_squares = capture_squares.union(affected_squares[1])
            else:
                new_movable = known_movable.union(affected_squares)
                return is_blockaded(board, new_movable)
    if len(capture_squares) > 0:
        board_copy = board.copy()
        for square in capture_squares:
            board_copy.remove_piece_at(square)
        return is_blockaded(board_copy, known_movable)
    return True

def get_affected_squares(unmovable_board, piece, start_square, original_board):
    board_copy = unmovable_board.copy()
    board_copy.turn = piece.color
    seen_squares = {start_square}
    new_squares = {start_square}
    pawns = chess.SquareSet(board_copy.pawns)
    captured_squares = chess.SquareSet()
    while(len(new_squares)) > 0:
        for square in new_squares.copy():
            new_squares.remove(square)
            # only happens if king is in check, which shouldn't be the case
            if piece.piece_type != chess.KING:
                attacking_squares = board_copy.attackers(not board_copy.turn, square)
                # non-pawns legal capture moves are legal moves anyways, so capturing moves don't free them
                attacking_squares = attacking_squares.intersection(pawns)
                if len(attacking_squares) > 0:
                    return attacking_squares
            _ = board_copy.set_piece_at(square, piece)
            moves = list(board_copy.legal_moves)
            capture_moves = [move for move in moves if board_copy.is_capture(move)]
            if len(capture_moves) > 0:
                capture_squares = [move.to_square for move in capture_moves]
                captured_squares = captured_squares.union(chess.SquareSet(capture_squares))
            if piece.piece_type == chess.PAWN:
                promotions = [move for move in moves if move.promotion is not None]
                for move in promotions:
                    promotion_piece = chess.Piece(move.promotion, piece.color)
                    promotion_affected = get_affected_squares(unmovable_board, promotion_piece, move.to_square, original_board)
                    if promotion_affected is not None:
                        return promotion_affected
            destinations = {move.to_square for move in moves}
            new_square_destinations = destinations.difference(seen_squares)
            new_squares = new_squares.union(new_square_destinations)
            seen_squares = seen_squares.union(new_square_destinations)
            _ = board_copy.remove_piece_at(square)
    if len(captured_squares) > 0:
        return (-1, capture_squares)
    return

f = open(os.path.join(RESULTS_BY_PLY_DIRECTORY, MAX_PLY_FILE), 'r')
max_ply_positions = f.read().splitlines() 
f.close()

#good test case: '8/8/7p/5p1P/5p1K/5Pp1/6P1/5kb1 b - - 0 1'

print('Checking max ply boards for blockades')
boards = [chess.Board(position) for position in max_ply_positions] #20399
blockaded_list = [is_blockaded(board) for board in boards] #20399
blockaded_boards = [boards[i] for i in range(len(boards)) if blockaded_list[i]] #20392
non_blockaded_boards = [boards[i] for i in range(len(boards)) if not blockaded_list[i]] #7
print('Done.')

def create_file(board_list, file_name, directory, extension = ".txt"):
    f_name = directory + file_name + extension
    f = open(f_name, 'w')
    positions = {re.sub('\ \d.*', '', board.fen().strip()) + "\n" for board in board_list}
    _ = f.writelines(positions)
    f.close()

create_file(non_blockaded_boards, "max_other", DETAILED_RESULTS_DIRECTORY)

def blockade_squares(square):
    offset_pawns = []
    square_rank = chess.square_rank(square)
    square_file = chess.square_file(square)
    if square_file < 7:
        if square_rank > 1:
            offset_pawns.append(chess.square(square_file + 1, square_rank - 1))
        if square_rank < 5:
            offset_pawns.append(chess.square(square_file + 1, square_rank + 1))
    if square_file < 6:
        if square_rank > 1:
            offset_pawns.append(chess.square(square_file + 2, square_rank - 1))
        offset_pawns.append(chess.square(square_file + 2, square_rank))
        if square_rank < 5:
            offset_pawns.append(chess.square(square_file + 2, square_rank + 1))
    if square_file < 5:
        offset_pawns.append(chess.square(square_file + 3, square_rank))
    return offset_pawns

def create_all_blockades(squares):
    if len(squares) == 0:
        all_blockades = []
        for file in range(2):
            for rank in range(1, 6):
                start_square = chess.square(file, rank)
                all_blockades = all_blockades + create_all_blockades([start_square])
        return all_blockades
    right_square = squares[-1]
    possible_continuations = blockade_squares(right_square)
    all_blockades = []
    for square in possible_continuations:
        blockade_endings = create_all_blockades(squares + [square])
        all_blockades = all_blockades + blockade_endings
    if chess.square_file(right_square) >= 6:
        all_blockades.append(squares)
    return(all_blockades)

def blockade_squares_to_squaresets(squares):
    board = chess.Board()
    white_pawns = chess.SquareSet(squares)
    black_locations = [square + 8 for square in squares]
    black_pawns = chess.SquareSet(black_locations)
    squaresets_tuple = (int(black_pawns), int(white_pawns))
    return squaresets_tuple

print('Generating basic pawn blockades...')
all_blockade_white_pawns = create_all_blockades([])
blockade_squaresets = [blockade_squares_to_squaresets(squares) for squares in all_blockade_white_pawns]
blockade_dict = dict()
for squaresets in blockade_squaresets:
    blockade_dict[squaresets[chess.WHITE]] = squaresets[chess.BLACK]
print('Done.')

#18924
blockaded_pawn_boards = [board for board in blockaded_boards if board.bishops == 0 and board.knights == 0 and board.queens == 0 and board.rooks == 0]
#1468
blockaded_non_pawn_boards = [board for board in blockaded_boards if not(board.bishops == 0 and board.knights == 0 and board.queens == 0 and board.rooks == 0)]

def check_pawns(board, allow_extra_pawns = False, pawn_dict = blockade_dict):
    white_pawns = int(board.pieces(chess.PAWN, chess.WHITE))
    black_pawns = int(board.pieces(chess.PAWN, chess.BLACK))
    if white_pawns in blockade_dict:
        black_blockade_pawns = blockade_dict[white_pawns]
        if black_blockade_pawns == black_pawns:
            return True
        elif allow_extra_pawns:
            return black_blockade_pawns & black_pawns == black_blockade_pawns
    elif allow_extra_pawns:
        white_blockade_pawns = [blockade_pawns for blockade_pawns in blockade_dict if white_pawns & blockade_pawns == blockade_pawns]
        if len(white_blockade_pawns) > 0:
            for white_blockades in white_blockade_pawns:
                black_blockade_pawns = blockade_dict[white_blockades]
                if black_pawns & black_blockade_pawns == black_blockade_pawns:
                    return True
    return False

print('Categorizing pawn blockades')
simple_blockade = [board for board in blockaded_pawn_boards if check_pawns(board)] #14146
non_simple_pawn_blockade = [board for board in blockaded_pawn_boards if not check_pawns(board)] #4778
simple_blockade_with_extra_pawns = [board for board in non_simple_pawn_blockade if check_pawns(board, True)] #4540
remaining_pawn_blockades = [board for board in non_simple_pawn_blockade if not check_pawns(board, True)] #238

def make_pawn_board(board):
    white_pawn_squares = board.pieces(chess.PAWN, chess.WHITE)
    black_pawn_squares = board.pieces(chess.PAWN, chess.BLACK)
    white_pawn = chess.Piece(chess.PAWN, chess.WHITE)
    black_pawn = chess.Piece(chess.PAWN, chess.BLACK)
    pawn_board = chess.Board()
    pawn_board.clear()
    for square in white_pawn_squares:
        pawn_board.set_piece_at(square, white_pawn)
    for square in black_pawn_squares:
        pawn_board.set_piece_at(square, black_pawn)
    return pawn_board

def is_wall_for_color(board, color):
    pawn_board = make_pawn_board(board)
    start_square = board.king(color)
    seen_squares = set([start_square])
    new_squares = set([start_square])
    pawn_board.turn = color
    if color == chess.WHITE:
        target_rank = 7
    else:
        target_rank = 0
    king_piece = chess.Piece(chess.KING, color)
    while len(new_squares) > 0:
        square = new_squares.pop()
        if chess.square_rank(square) == target_rank:
            return False
        pawn_board.set_piece_at(square, king_piece)
        legal_moves = pawn_board.legal_moves
        king_moves = [move for move in legal_moves if move.from_square == square]
        destinations = {move.to_square for move in king_moves}
        new_king_squares = destinations.difference(seen_squares)
        new_squares = new_squares.union(new_king_squares)
        seen_squares = seen_squares.union(new_king_squares)
        pawn_board.remove_piece_at(square)
    return True

def is_wall(board):
    if is_wall_for_color(board, chess.WHITE):
        return is_wall_for_color(board, chess.BLACK)
    return False

wall_pawn_blockades = [board for board in remaining_pawn_blockades if is_wall(board)] #238
non_wall_pawn_blockades = [board for board in remaining_pawn_blockades if not is_wall(board)] #0
print('Done.')

print('Categorizing blockades with pieces')
simple_blockade_with_pieces = [board for board in blockaded_non_pawn_boards if check_pawns(board)] #1100
non_simple_piece_blockade = [board for board in blockaded_non_pawn_boards if not check_pawns(board)] #368
simple_piece_blockade_with_extra_pawns = [board for board in non_simple_piece_blockade if check_pawns(board, True)] #319
remaining_piece_blockades = [board for board in non_simple_piece_blockade if not check_pawns(board, True)] #49
wall_piece_blockades = [board for board in remaining_piece_blockades if is_wall(board)] #4
non_wall_piece_blockades = [board for board in remaining_piece_blockades if not is_wall(board)] #45
stuck_king_blockades = [board for board in non_wall_piece_blockades if find_unmovable_pieces(board).kings != 0] #45
other_piece_blockades = [board for board in non_wall_piece_blockades if find_unmovable_pieces(board).kings == 0] #0
print('Done')

print('Creating blockade files')
create_file(simple_blockade, "max_basic_blockade", DETAILED_RESULTS_DIRECTORY)
create_file(simple_blockade_with_extra_pawns, "max_basic_blockade_with_extra_pawns", DETAILED_RESULTS_DIRECTORY)
create_file(wall_pawn_blockades, "max_other_wall_pawn_blockades", DETAILED_RESULTS_DIRECTORY)
create_file(non_wall_pawn_blockades, "max_other_pawn_blockades", DETAILED_RESULTS_DIRECTORY)
create_file(simple_blockade_with_pieces, "max_basic_piece_blockade", DETAILED_RESULTS_DIRECTORY)
create_file(simple_piece_blockade_with_extra_pawns, "max_basic_piece_blockade_with_extra_pieces", DETAILED_RESULTS_DIRECTORY)
create_file(wall_piece_blockades, "max_other_wall_piece_blockades", DETAILED_RESULTS_DIRECTORY)
create_file(stuck_king_blockades, "max_trapped_king", DETAILED_RESULTS_DIRECTORY)
create_file(other_piece_blockades, "max_other_piece_blockades", DETAILED_RESULTS_DIRECTORY)
print('Done.')